'use client';

import { useEffect } from 'react';
import { flushTelemetry, reportTelemetry } from '@/services/telemetry';

export default function BrowserTelemetry() {
    useEffect(() => {
        const load = () => {
            // Run after loadEventEnd is populated.
            window.setTimeout(() => {
                const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
                if (navigation?.loadEventEnd) reportTelemetry('page_load', 'page', 'ok', navigation.loadEventEnd);
            }, 0);
        };
        const error = () => reportTelemetry('js_error', 'page', 'error');
        const rejection = () => reportTelemetry('unhandled_rejection', 'page', 'error');
        const hidden = () => { if (document.hidden) flushTelemetry(); };
        if (document.readyState === 'complete') load();
        else window.addEventListener('load', load, { once: true });
        window.addEventListener('error', error);
        window.addEventListener('unhandledrejection', rejection);
        window.addEventListener('pagehide', flushTelemetry);
        document.addEventListener('visibilitychange', hidden);
        return () => {
            window.removeEventListener('load', load);
            window.removeEventListener('error', error);
            window.removeEventListener('unhandledrejection', rejection);
            window.removeEventListener('pagehide', flushTelemetry);
            document.removeEventListener('visibilitychange', hidden);
        };
    }, []);
    return null;
}
