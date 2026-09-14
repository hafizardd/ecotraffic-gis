# Observability production — EcoTraffic GIS

Implementasi tahap awal ini memakai Grafana OSS, Prometheus, Loki, Alloy,
node-exporter, cAdvisor, dan redis-exporter. Tidak ada instrumentation traces.
Aplikasi mengeluarkan JSON logs ke stdout dan metrics Prometheus melalui port
internal 9101. Browser mengirim batch event yang sudah disampling ke API.

## Apa yang tersedia

| Area | Pengukuran |
| --- | --- |
| API | Request rate/status per template route, active requests, waktu headers, durasi sampai body selesai, request ID di log dan response |
| Database | Durasi eksekusi SQL dan jumlah error untuk engine sync/async; tidak merekam SQL atau parameternya |
| Video MJPEG | Stream aktif, waktu frame pertama di-yield server, jumlah frame/byte, waktu Redis GET, polling tanpa frame, error Redis |
| Video HLS | Stream aktif, byte media, waktu fetch playlist upstream, kegagalan playlist/media upstream |
| Tracker | Durasi inference per kamera, FPS frame tersimpan, timestamp penyimpanan terakhir, error capture/inference/publish/snapshot |
| Celery | Task selesai per state, durasi task, task aktif, waktu penyelesaian terakhir; mendukung prefork |
| Server | CPU, RAM, disk dan network host; CPU/RAM container; Redis health/memory/connections dan queue `inference` |
| Browser | Fetch sampai headers/body selesai diproses, page load, JS error, unhandled rejection, event load/error/timeout MJPEG |

Dashboard `EcoTraffic / EcoTraffic Production` dan datasource diprovisioning
secara otomatis. Panel logs dapat dibuka lebih lanjut melalui Explore → Loki.
Prometheus mengevaluasi 8 alert rules; alert yang firing dapat dicari dengan
query `ALERTS{alertstate="firing"}` di Grafana Explore (Prometheus).
Belum ada pengiriman notifikasi email/Slack/WhatsApp atau Alertmanager.

## Setup production

Target konfigurasi: satu host Linux dengan Docker Engine dan **Docker Compose
2.24.4 atau lebih baru** (`!override` digunakan untuk port). Sesuaikan domain,
DNS, TLS, dan reverse proxy milik deployment sebelum membuka aplikasi ke pengguna.
Gunakan backend/.env dan database yang memang milik environment tujuan.

Dari root repository:

```bash
cp observability/.env.example observability/.env
```

Edit `observability/.env`:

```dotenv
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<password-acak-yang-panjang>
GRAFANA_PORT=3001
APP_ENV=production
CORS_ORIGINS=https://eco.example.com
PUBLIC_API_URL=https://api.eco.example.com
PUBLIC_WS_URL=wss://api.eco.example.com
BROWSER_SAMPLE_RATE=0.1
```

`CORS_ORIGINS` adalah origin halaman frontend, tanpa trailing slash. Beberapa
origin dipisahkan koma tanpa spasi. `PUBLIC_API_URL` adalah alamat API yang bisa
diakses browser, bukan hostname Docker. Rate `0.1` memilih sekitar 10% page session;
untuk verifikasi awal gunakan `1`, kemudian turunkan kembali dan rebuild frontend.
Jangan menaruh secret di variabel `PUBLIC_*`/`NEXT_PUBLIC_*`.

```bash
dc() {
  docker compose --env-file backend/.env --env-file observability/.env \
    -f docker-compose.yml -f docker-compose.observability.yml "$@"
}

dc config --quiet
dc up -d --build
dc ps
dc exec -T backend python -m app.observability.verify
```

`up --build` merekreasi service aplikasi yang berubah; jalankan saat jendela
rollout yang sesuai. Migrasi/seed database tetap mengikuti prosedur deployment
aplikasi yang sudah ada; observability tidak menambah tabel atau migrasi.

Overlay mengubah frontend menjadi `next build` + `next start`, bukan dev server.
Variabel browser ditanam **saat build**. Mengubah environment saat runtime saja
tidak memperbarui URL/rate telemetry di bundle; jalankan `dc up -d --build frontend`.

Port host setelah overlay:

| Service | Akses |
| --- | --- |
| Frontend | `127.0.0.1:3000` untuk reverse proxy host |
| API/WebSocket | `127.0.0.1:8080` untuk reverse proxy host |
| Grafana | `127.0.0.1:3001` secara default |
| Postgres, Redis, Prometheus, Loki, exporters | Hanya network Docker; tidak dipublikasikan ke host |

Backend exporter ada di `backend:9101/metrics`, bukan API publik `/metrics`.
Jika reverse proxy berjalan dalam Docker, hubungkan ke network aplikasi dan
pakai `frontend:3000`/`backend:8000`. Proxy WebSocket harus meneruskan upgrade;
proxy MJPEG perlu mematikan response buffering dan memakai read timeout yang
sesuai durasi stream. Terapkan body limit 8 KB dan rate limit per IP khusus
`POST /api/telemetry` di ingress. API juga memiliki batas ukuran, batch, origin,
dan rate keseluruhan per proses; pemeriksaan origin bukan autentikasi client.

Untuk mengakses Grafana dari laptop melalui SSH:

```bash
ssh -L 3001:127.0.0.1:3001 user@server
```

Buka `http://localhost:3001`, login dengan kredensial yang dikonfigurasi, lalu
buka Dashboards → EcoTraffic → EcoTraffic Production. Password admin environment
hanya menginisialisasi database Grafana pertama kali; pergantian password
berikutnya dilakukan lewat Grafana atau admin CLI.

## Memakai dashboard untuk diagnosis

1. Buka aplikasi dan pilih kamera. Tunggu sekurangnya satu interval scrape
   (15 detik) dan batch browser (5 detik). Untuk p95/rate, kumpulkan traffic
   selama beberapa menit; panel kosong sebelum event pertama adalah normal.
2. Periksa `Scrape health`. `up=1` berarti exporter bisa di-scrape, belum tentu
   kamera atau database sehat. Lihat juga freshness/error masing-masing komponen.
3. Untuk fetch lambat, bandingkan p95 browser dan p95 API. Jika API ikut naik,
   lihat DB query p95, CPU, RAM, dan task worker. Jika browser jauh lebih lambat,
   periksa network, payload size, dan parsing browser. Perbandingan ini agregat,
   bukan korelasi satu request seperti tracing.
4. Untuk video lambat, periksa active streams, payload throughput, first frame,
   Redis errors/missing snapshots, tracker FPS dan freshness. Frame tracker
   normal tetapi throughput mentok mengarahkan pemeriksaan ke jaringan/proxy.
5. Saat task lambat atau data tidak diperbarui, periksa queue depth, active tasks,
   task duration/state, waktu completion terakhir, lalu logs worker/beat.
6. Buka Explore → Loki pada rentang waktu insiden. Cari log dengan query berikut.

```logql
{stack="ecotraffic", service="backend"} | json | level="ERROR"
```

```logql
{stack="ecotraffic", service="backend"} | json | message="http_request" | duration_ms > 1000
```

```logql
{stack="ecotraffic"} | json | request_id="ID-dari-header-X-Request-ID"
```

```logql
{stack="ecotraffic", service="tracker"} |= "tracking_inference_failed"
```

Jika banyak Compose project memakai label observability pada host yang sama,
filter logs juga dengan `project="nama-project"`. cAdvisor membaca container
host; dashboard container menggabungkan nama service yang sama lintas project.

## Batas interpretasi

- `eco_http_duration_seconds` mengecualikan MJPEG/HLS dan event streams; koneksi
  video bisa berlangsung lama. HTTP request counter bertambah ketika koneksi
  selesai. Headers metric tersedia lebih awal.
- `eco_video_first_frame_seconds` adalah waktu dari mulai generator sampai
  frame pertama di-yield. Bukan waktu gambar terlihat di perangkat pengguna.
- `video_load_event` memakai event `img.onload` native. Perilaku MJPEG bergantung
  browser dan tidak selalu merepresentasikan frame pertama. Timeout 15 detik
  berarti belum menerima load/error event, bukan bukti kamera mati. Implementasi
  ini belum mengukur per-frame render FPS atau freeze video di browser.
- Freshness tracker mengukur waktu frame berhasil disimpan, bukan timestamp asli
  CCTV sebelum decoder. Delay upstream masih mungkin terjadi meskipun angka ini kecil.
- Browser `fetch_body` mencakup pembacaan body dan JSON parsing, belum React render.
  Instrumentation fetch mencakup helper pada `src/services/api.ts`, bukan seluruh
  resource browser, tile MapLibre, atau download yang dilakukan langsung lewat link.
- Browser telemetry disampling per page session, dibatasi 20 event per batch,
  maksimal satu batch reguler per 5 detik. Queue berlebih dibuang, request tanpa
  kredensial, pengiriman gagal tidak diulang. Counts bukan jumlah seluruh pengguna.
- Browser hanya mengirim enum kategori/outcome dan durasi, tanpa URL lengkap,
  query, user ID, stack JS atau isi chat. Metrics dari browser tetap data yang
  tidak tepercaya; gunakan untuk diagnosis agregat.
- Query DB metrics belum mengukur waktu menunggu connection pool. Tidak ada
  profiler GPU, tracing, ataupun pengukuran kapasitas concurrent-user pada fase ini.
- Queue depth memakai Redis DB 0 dan key `inference`, sesuai default broker.
  Sesuaikan `REDIS_EXPORTER_CHECK_SINGLE_KEYS` jika broker DB atau queue berubah.
  Redis exporter memakai `REDIS_URL` dari backend/.env; pastikan hostname Docker.
- Task Celery berstatus SUCCESS belum menjamin semua kalkulasi bisnis berhasil
  jika task menangkap exception sendiri; tetap periksa error logs.

## Operasional dan kapasitas

- Prometheus: retensi 14 hari dengan batas blok TSDB 5 GB (WAL/head memerlukan
  ruang tambahan). Loki: retensi 7 hari, penghapusan asynchronous oleh compactor.
  Docker logs: maksimal 3 file × 10 MB per service yang dikonfigurasi.
- Semua storage menggunakan named volumes. Jangan memakai `down -v` untuk
  deployment ini karena juga menghapus volume database aplikasi. Backup
  Grafana dan database sesuai kebijakan deployment; logs/metrics dapat tumbuh.
- Mulai dengan memantau konsumsi stack bersama YOLO. Ukuran host yang tepat
  ditentukan oleh traffic, jumlah kamera, dan volume logs; pisahkan observability
  ke host lain jika terjadi perebutan RAM/CPU/disk.
- Alloy membutuhkan Docker socket untuk logs; mount `:ro` tidak menjadikan
  Docker API read-only. cAdvisor memerlukan akses privileged dan mount host
  untuk membaca statistik container. Jalankan hanya image tepercaya dan batasi
  akses network ke stack ini. node-exporter mengukur host Linux, bukan laptop
  fisik jika Docker berjalan di VM/Desktop.
- Label metrics tidak memuat request ID, raw URL, query atau filename HLS.
  Kamera tracker adalah daftar terkonfigurasi; task label berasal dari registry task.
- Log JSON mempertahankan field `extra`, meredaksi nama field sensitif, dan
  merekam exception type/stack locations tanpa exception text. Hindari memasukkan
  secret ke message log biasa; formatter tidak menjamin redaksi arbitrary text.
- Worker entrypoint membersihkan file metrics ephemeral khusus container sebelum
  prefork. Jangan membagikan direktori itu antar container. API dan tracker
  masing-masing memakai satu proses, sesuai Compose. Jangan menambahkan beberapa
  worker Uvicorn ke satu container tanpa menyesuaikan exporter/multiprocess.
- Alert threshold awal adalah titik awal, bukan SLO final. Sesuaikan dengan
  baseline traffic; periksa dengan Explore → Prometheus → `ALERTS`.

## Verifikasi konfigurasi dan perubahan

```bash
dc run --rm --no-deps --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
dc run --rm --no-deps alloy validate /etc/alloy/config.alloy
dc run --rm --no-deps loki -config.file=/etc/loki/config.yml -verify-config=true
```

Restart setelah mengubah config: `dc restart prometheus loki alloy`.
Grafana membaca dashboard provisioning berkala; perubahan datasource memerlukan
restart Grafana. `dc exec -T backend python -m app.observability.verify` memeriksa
kesiapan Grafana, tujuh target scrape, dan keberadaan backend logs di Loki.
Untuk memverifikasi browser, set sampling `1`, rebuild, buka aplikasi lalu cek
`eco_browser_events_total`; kembalikan sampling setelah pemeriksaan.

Referensi desain: [Prometheus Python multiprocess](https://prometheus.github.io/client_python/multiprocess/),
[Alloy Docker logs](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.docker/),
[Celery signals](https://docs.celeryq.dev/en/stable/userguide/signals.html).

## Hasil verifikasi implementasi

Pada branch `feat/observability-stack`:

- Test observability/API/startup: 13 passed; termasuk route cardinality, JSON
  redaction, browser ingestion limits, ASGI streaming/cancellation, DB timings,
  MJPEG cleanup/error, dan pembacaan metrics Celery dari proses berbeda.
- Regresi backend non-CV: 248 passed, 13 skipped, 1 failed. Kegagalan
  `test_dispatch_scope_selection_fallback_is_low_confidence` juga direproduksi
  pada `origin/development` (baseline: 241 passed, 13 skipped, 1 failed).
  Pengujian deterministik menonaktifkan API key LLM melalui environment.
- Regresi CV/tracker pada image Python 3.10 + OpenCV/PyTorch: 18 passed.
- Frontend: typecheck, lint, seluruh 9 file test termasuk telemetry, dan build
  production berhasil; image production juga diuji melayani HTTP 200. Dockerfile production menyelaraskan npm ke 11.6.2 karena
  npm 10 pada base image menolak lockfile yang berhasil dibaca npm 11.
- Validator resmi Prometheus (termasuk 8 rules), Loki, Alloy, dan Compose lolos.
- Smoke test Docker terisolasi: tujuh scrape jobs `up`, metrics API/browser
  masuk Prometheus, logs masuk Loki, dashboard Grafana terprovisioning, dan task
  `celery.accumulate` berhasil melalui prefork serta counter-nya terbaca.
  Tracker pada smoke test adalah sumber metrics sintetis; koneksi kamera live
  dan kapasitas beban production belum diuji.

Stack smoke test tidak memakai database aplikasi yang sedang berjalan.
