/** Renders "H2O" or "C6H12O6" with subscripted counts (fonts lack Unicode subscripts). */
export const Formula: React.FC<{ formula: string; style?: React.CSSProperties }> = ({ formula, style }) => {
  const parts = formula.split(/(\d+)/).filter(Boolean);
  return (
    <span style={style}>
      {parts.map((part, i) =>
        /^\d+$/.test(part) ? (
          <sub key={i} style={{ fontSize: "0.62em", verticalAlign: "-0.28em" }}>
            {part}
          </sub>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  );
};
