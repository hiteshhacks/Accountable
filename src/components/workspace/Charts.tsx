// Small SVG charts for the Overview page. Colours come from --viz-* roles (validated reference
// palette, fixed slot order); text always uses text tokens; each mark has a hover tooltip.

export interface Slice {
  label: string;
  value: number;
}

const SLOTS = ['var(--viz-1)', 'var(--viz-2)', 'var(--viz-3)', 'var(--viz-4)', 'var(--viz-5)'];

/** Top five categories in fixed slots; the rest fold into "Other". */
export function foldSlices(counts: Record<string, number>, max = 5): Slice[] {
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const top = sorted.slice(0, max).map(([label, value]) => ({ label, value }));
  const rest = sorted.slice(max).reduce((s, [, v]) => s + v, 0);
  return rest > 0 ? [...top, { label: 'Other', value: rest }] : top;
}

function polar(cx: number, cy: number, r: number, angle: number) {
  const a = ((angle - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
}

export function DonutChart({ slices, centerLabel }: { slices: Slice[]; centerLabel: string }) {
  const total = slices.reduce((s, x) => s + x.value, 0);
  const color = (i: number, label: string) => (label === 'Other' ? 'var(--viz-other)' : SLOTS[i % SLOTS.length]);
  const size = 180, cx = 90, cy = 90, r = 72, stroke = 22;
  let angle = 0;

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${centerLabel}: ${total}`}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--viz-track)" strokeWidth={stroke} />
        {total > 0 && slices.map((s, i) => {
          const sweep = (s.value / total) * 360;
          const gap = slices.length > 1 ? 1.2 : 0; // 2px-ish surface gap between segments
          const start = angle + gap / 2;
          const end = angle + sweep - gap / 2;
          angle += sweep;
          if (slices.length === 1) {
            return (
              <circle key={s.label} cx={cx} cy={cy} r={r} fill="none" stroke={color(i, s.label)} strokeWidth={stroke}>
                <title>{`${s.label}: ${s.value} (100%)`}</title>
              </circle>
            );
          }
          const [x1, y1] = polar(cx, cy, r, start);
          const [x2, y2] = polar(cx, cy, r, end);
          const large = end - start > 180 ? 1 : 0;
          return (
            <path key={s.label} d={`M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`} fill="none"
              stroke={color(i, s.label)} strokeWidth={stroke}>
              <title>{`${s.label}: ${s.value} (${Math.round((s.value / total) * 100)}%)`}</title>
            </path>
          );
        })}
        <text x={cx} y={cy - 2} textAnchor="middle" className="ws-serif" fontSize="30" fill="var(--ws-text)">{total}</text>
        <text x={cx} y={cy + 18} textAnchor="middle" fontSize="10" fontWeight="600" letterSpacing="1.5" fill="var(--ws-text-2)">
          {centerLabel.toUpperCase()}
        </text>
      </svg>

      <ul className="w-full min-w-0 flex-1 space-y-2">
        {slices.map((s, i) => (
          <li key={s.label} className="flex items-center gap-3 rounded-xl border px-3 py-2 text-[13px]"
            style={{ borderColor: 'var(--ws-border)', background: 'var(--ws-bg)' }}>
            <span className="size-3 shrink-0 rounded-full" style={{ background: color(i, s.label) }} />
            <span className="min-w-0 flex-1 truncate font-semibold" title={s.label}>{s.label}</span>
            <span className="tabular-nums">{s.value}</span>
            <span className="ws-chip ws-chip-gold px-1.5 py-0 text-[10px]">
              {total ? Math.round((s.value / total) * 100) : 0}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export interface BarDatum {
  label: string;
  value: number;
  title: string;
}

/** Single series, so one colour and no legend; the card title names the measure. */
export function BarChart({ data }: { data: BarDatum[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const height = 170;
  return (
    <div className="flex h-[230px] items-end gap-3 px-1" role="img" aria-label="Rows classified per day">
      {data.map((d) => {
        const h = d.value === 0 ? 3 : Math.max(10, (d.value / max) * height);
        return (
          <div key={d.label} className="flex flex-1 flex-col items-center gap-2" title={d.title}>
            <span className="text-[11px] font-semibold tabular-nums" style={{ color: 'var(--ws-text-2)' }}>{d.value}</span>
            <div className="w-full max-w-[44px] rounded-t-[6px]"
              style={{ height: h, background: d.value ? 'var(--ws-gold-btn)' : 'var(--viz-track)' }} />
            <span className="text-[11px]" style={{ color: 'var(--ws-muted)' }}>{d.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Semicircle meter for a single 0-1 value. */
export function ScoreGauge({ value, label, sublabel }: { value: number | null; label: string; sublabel: string }) {
  const r = 70, cx = 90, cy = 90, stroke = 14;
  const arc = (to: number) => {
    const [x1, y1] = polar(cx, cy, r, -90);
    const [x2, y2] = polar(cx, cy, r, -90 + 180 * to);
    return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
  };
  return (
    <div className="flex flex-col items-center">
      <svg width="180" height="105" viewBox="0 0 180 105" role="img" aria-label={`${label}: ${value === null ? 'no data' : value.toFixed(2)}`}>
        <path d={arc(1)} fill="none" stroke="var(--viz-track)" strokeWidth={stroke} strokeLinecap="round" />
        {value !== null && value > 0 && (
          <path d={arc(Math.min(1, value))} fill="none" stroke="var(--ws-gold-btn)" strokeWidth={stroke} strokeLinecap="round">
            <title>{`${label}: ${value.toFixed(2)}`}</title>
          </path>
        )}
        <text x={cx} y={cy - 4} textAnchor="middle" className="ws-serif" fontSize="30" fill="var(--ws-text)">
          {value === null ? '—' : value.toFixed(2)}
        </text>
      </svg>
      <p className="mt-1 text-[11px] font-bold tracking-[0.14em]" style={{ color: 'var(--ws-gold)' }}>{label.toUpperCase()}</p>
      <p className="mt-2 max-w-[260px] text-center text-xs" style={{ color: 'var(--ws-text-2)' }}>{sublabel}</p>
    </div>
  );
}
