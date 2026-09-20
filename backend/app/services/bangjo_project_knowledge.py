"""Static, hand-written project knowledge for Bang Jo's ``scope=meta`` answers.

This is deliberately NOT queried from the live DB: it is stable product
documentation, versioned in source, so the assistant can describe the project
itself without inventing figures it cannot retrieve. Keep every slice short and
factual; numbers that change belong in a context builder, not here.
"""

import re
from datetime import datetime, timezone

PROJECT_KNOWLEDGE: dict[str, str] = {
    "tentang": (
        "EcoTraffic-GIS adalah dasbor perencanaan transportasi publik berbasis WebGIS "
        "untuk Yogyakarta. Tujuannya membantu memilih prioritas intervensi lalu lintas "
        "lewat analisis emisi kendaraan dan potensi aktivitas kawasan, bukan sekadar "
        "menampilkan peta."
    ),
    "live_replay": (
        "Peta aktivitas punya dua mode. Mode 'Live' membaca pembacaan terbaru dari kamera, "
        "jadi angkanya mengikuti kondisi terkini. Mode 'Replay' memakai profil statis 24 jam "
        "prakomputasi; pilih jam tertentu untuk melihat pola khas jam itu. Nilai replay bisa "
        "merupakan hasil interpolasi, jadi sifatnya perkiraan, bukan pengamatan langsung."
    ),
    "skor_aktivitas": (
        "Skor potensi aktivitas (skor_total_ahp, rentang 0-100) menggabungkan tiga faktor: "
        "kepadatan POI, jumlah penduduk, dan volume lalu lintas. Skor diklasifikasikan ke lima "
        "kelas, dari 'Sangat Rendah' sampai 'Sangat Tinggi'. Makin tinggi skor, makin tinggi "
        "potensi aktivitas sel grid tersebut."
    ),
    "emisi": (
        "Emisi dihitung dari jumlah kendaraan yang terdeteksi kamera dikalikan faktor emisi "
        "tiap polutan per satuan waktu, lalu dijumlahkan per segmen jalan dan per kamera. "
        "Satuannya gram per jam dan ditampilkan sebagai kg per jam. Polutan mencakup CO2, NOx, "
        "SO2, CO, PM, dan HC."
    ),
    "sumber_data": (
        "Data berasal dari hitungan kendaraan CCTV + YOLO, survei POI dan penduduk, serta skor "
        "AHP turunannya. Nilai yang tidak punya kamera langsung diambil dari segmen terdekat "
        "dan ditandai sebagai perkiraan; data profil statis 24 jam ditandai terpisah agar tidak "
        "disangka arus langsung."
    ),
    "kemampuan": (
        "Bang Jo bisa menjelaskan emisi per koridor, peringkat potensi aktivitas sel grid, "
        "kualitas halte, kebutuhan intervensi ASI (Avoid/Shift/Improve), dan cara kerja proyek "
        "ini. Bang Jo TIDAK bisa menjawab topik di luar transportasi, emisi, dan dashboard ini, "
        "dan tidak bisa mengubah data."
    ),
}

# Indonesian + English phrasings, since users mix languages. Ordered so the most
# specific intent wins when several overlap.
_META_KEYWORDS: list[tuple[str, str]] = [
    (
        "tentang",
        r"\b(apa itu|apakah itu|apa sih|what is|what's)\b.*\b"
        r"(ecotraffic|eco ?traffic|aplikasi|dasbor|dashboard|proyek|project|webgis|situs|sistem)\b",
    ),
    ("tentang", r"\beco ?traffic\b"),
    (
        "live_replay",
        r"\b(apa bedanya|bedanya|beda|perbedaan|difference)\b.*\b"
        r"(live|replay|real ?time|histori|historis|riwayat|mode)\b",
    ),
    ("live_replay", r"\b(mode)\s+(live|replay)\b"),
    (
        "skor_aktivitas",
        r"\b(apa itu|apakah|what is|cara hitung|gimana cara|bagaimana cara|dari apa|terdiri dari|komponen|unsur)\b"
        r".*\b(skor|ranking|peringkat|potensi|aktivitas|activity|ahp)\b",
    ),
    ("skor_aktivitas", r"\b(klasifikasi|kelas|tier|tingkatan)\b.*\b(potensi|aktivitas|ahp)\b"),
    (
        "emisi",
        r"\b(apa itu|what is|cara hitung|gimana cara|bagaimana cara|dari mana|rumus|how)\b"
        r".*\b(emisi|emission|kg ?/ ?jam|gram per jam)\b",
    ),
    ("sumber_data", r"\b(data|datanya)\b.*\b(dari mana|dari|bersumber|sumber|source|asal)\b"),
    ("sumber_data", r"\b(sumber|source)\b.*\b(data)\b"),
    ("sumber_data", r"\b(data)\b.*\b(fresh|stale|basi|kadaluarsa|terbaru|update|perkiraan)\b"),
    (
        "kemampuan",
        r"\b(kamu|anda|bang ?jo)\b.*\b(bisa apa|bisa apa saja|kemampuan|capabilities|ngapain)\b",
    ),
]

_META_PATTERNS: list[tuple[str, re.Pattern]] = [
    (topic, re.compile(pattern, re.IGNORECASE)) for topic, pattern in _META_KEYWORDS
]

# Fallback slices when the wording is clearly about the project but matches no
# specific keyword: the project identity, its data provenance, and its limits.
_FALLBACK_TOPICS = ("tentang", "sumber_data", "kemampuan")


def is_meta_query(text: str) -> bool:
    """True when the question is about the project itself, not a data lookup."""
    return any(pattern.search(text or "") for _, pattern in _META_PATTERNS)


def build_meta_context(text: str) -> dict:
    """Static project-knowledge slice instead of a SQL query.

    Returns every slice matched by the question; a project-shaped question with
    no specific match gets the default slices. No DB access, no LLM call.
    """
    topics = list(dict.fromkeys(topic for topic, pattern in _META_PATTERNS if pattern.search(text or "")))
    if not topics:
        topics = list(_FALLBACK_TOPICS)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "meta",
        "topik": topics,
        "pengetahuan": {topic: PROJECT_KNOWLEDGE[topic] for topic in topics},
        "catatan": (
            "Ini pengetahuan proyek yang statis. Jawab dari sini walau tidak ada data live, "
            "dan jangan mengarang angka pengukuran."
        ),
    }
