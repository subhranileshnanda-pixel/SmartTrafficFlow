const LEVEL_COLOR = { LOW: "#3ddc84", MEDIUM: "#ffb020", HIGH: "#ff5a4d" };
const LAMP = { RED: "#ff5a4d", YELLOW: "#ffb020", GREEN: "#3ddc84" };

const title = (road) => road.charAt(0) + road.slice(1).toLowerCase();

// Where each arm's signal, queue bar, label and emergency ring sit (400 x 400 drawing)
const ARMS = {
  NORTH: {
    light: { cx: 262, cy: 105, horizontal: false },
    queue: (len) => ({ x: 205, y: 150 - len, width: 30, height: len }),
    label: { x: 200, y: 18, anchor: "middle" },
    ring: { x: 160, y: 0, width: 80, height: 160 },
  },
  SOUTH: {
    light: { cx: 138, cy: 295, horizontal: false },
    queue: (len) => ({ x: 165, y: 250, width: 30, height: len }),
    label: { x: 200, y: 376, anchor: "middle" },
    ring: { x: 160, y: 240, width: 80, height: 160 },
  },
  WEST: {
    light: { cx: 105, cy: 135, horizontal: true },
    queue: (len) => ({ x: 150 - len, y: 165, width: len, height: 30 }),
    label: { x: 8, y: 264, anchor: "start" },
    ring: { x: 0, y: 160, width: 160, height: 80 },
  },
  EAST: {
    light: { cx: 295, cy: 265, horizontal: true },
    queue: (len) => ({ x: 250, y: 205, width: len, height: 30 }),
    label: { x: 392, y: 132, anchor: "end" },
    ring: { x: 240, y: 160, width: 160, height: 80 },
  },
};

function Light({ cx, cy, horizontal, state }) {
  const w = horizontal ? 58 : 24;
  const h = horizontal ? 24 : 58;
  return (
    <g>
      <rect x={cx - w / 2} y={cy - h / 2} width={w} height={h} rx="9" className="housing" />
      {["RED", "YELLOW", "GREEN"].map((c, i) => {
        const off = (i - 1) * 18;
        const on = state === c;
        return (
          <circle
            key={c}
            cx={horizontal ? cx + off : cx}
            cy={horizontal ? cy : cy + off}
            r="6.5"
            fill={on ? LAMP[c] : "#2a3d47"}
            style={on ? { filter: `drop-shadow(0 0 7px ${LAMP[c]})` } : undefined}
          />
        );
      })}
    </g>
  );
}

export default function Junction({ signals, densities, emergencyRoads }) {
  const current = signals.current_road;
  let big;
  let small;
  if (signals.phase === "ALL_RED") {
    big = "ALL";
    small = "red";
  } else if (signals.emergency_mode) {
    big = "EMG";
    small = `${title(current)} priority`;
  } else {
    big = Math.ceil(signals.timer);
    small = `${title(current)} ${signals.phase.toLowerCase()}`;
  }

  return (
    <svg viewBox="0 0 400 400" className="junction" role="img" aria-label="Live junction diagram">
      {/* roads */}
      <rect x="160" y="0" width="80" height="400" className="road-fill" />
      <rect x="0" y="160" width="400" height="80" className="road-fill" />
      <rect x="160" y="160" width="80" height="80" className="centre-fill" />

      {/* centre lines */}
      <g className="road-dash">
        <line x1="200" y1="44" x2="200" y2="150" />
        <line x1="200" y1="250" x2="200" y2="356" />
        <line x1="8" y1="200" x2="150" y2="200" />
        <line x1="250" y1="200" x2="392" y2="200" />
      </g>

      {/* stop lines */}
      <g className="stop-line">
        <line x1="200" y1="150" x2="240" y2="150" />
        <line x1="160" y1="250" x2="200" y2="250" />
        <line x1="150" y1="160" x2="150" y2="200" />
        <line x1="250" y1="200" x2="250" y2="240" />
      </g>

      {Object.entries(ARMS).map(([road, arm]) => {
        const d = densities[road] || { count: 0, score: 0, level: "LOW" };
        const len = Math.min(100, (d.score / 12) * 100);
        const q = arm.queue(len);
        const color = LEVEL_COLOR[d.level];
        return (
          <g key={road}>
            {len > 0 && <rect {...q} rx="4" fill={color} opacity="0.85" />}
            {emergencyRoads.includes(road) && <rect {...arm.ring} className="emg-ring" />}
            <Light {...arm.light} state={signals.states[road]} />
            <text x={arm.label.x} y={arm.label.y} textAnchor={arm.label.anchor} className="arm-name">
              {title(road)}
            </text>
            <text x={arm.label.x} y={arm.label.y + 16} textAnchor={arm.label.anchor} className="arm-info">
              <tspan fill={color} fontWeight="700">{d.level}</tspan>
              <tspan fill="#93a9b3">{`  ${d.count} vehicles`}</tspan>
            </text>
          </g>
        );
      })}

      {/* countdown in the centre */}
      <text x="200" y="207" textAnchor="middle" className="centre-big">{big}</text>
      <text x="200" y="227" textAnchor="middle" className="centre-small">{small}</text>
    </svg>
  );
}