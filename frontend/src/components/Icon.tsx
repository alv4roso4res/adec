// Ícones de traço (24x24) desenhados à mão: evita instalar biblioteca de ícones.
const PATHS = {
  activity: 'M3 12h4l3 8 4-16 3 8h4',
  chart: 'M5 20v-8M12 20V5M19 20v-11M3 20h18',
  pull: 'M6 8v8M11 6h4a3 3 0 0 1 3 3v7M13 4l-2 2 2 2',
  users: 'M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.2c1.8.6 3 2.9 3 5.8',
  box: 'M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5',
  commit: 'M12 3v6M12 15v6',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  x: 'M7 7l10 10M17 7L7 17',
  clock: 'M12 8v4l2.5 2',
  minus: 'M7 12h10',
  external: 'M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5',
} as const

// Círculos extras de alguns ícones (cx, cy, r).
const CIRCLES: Partial<Record<IconName, [number, number, number][]>> = {
  pull: [[6, 18, 2], [6, 6, 2], [18, 18, 2]],
  users: [[9, 8, 3.5]],
  commit: [[12, 12, 3]],
  clock: [[12, 12, 8]],
}

export type IconName = keyof typeof PATHS

interface IconProps {
  name: IconName
  size?: number
  className?: string
}

function Icon({ name, size = 18, className }: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
      {CIRCLES[name]?.map(([cx, cy, r]) => (
        <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={r} />
      ))}
    </svg>
  )
}

export default Icon
