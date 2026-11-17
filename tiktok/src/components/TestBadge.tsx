import { Interactive } from "remotion";
import { HEADING_FONT } from "../fonts.ts";

/** Marks pipeline tests and renders made with temporary audio. Never publish these. */
export const TestBadge: React.FC = () => {
  return (
    <Interactive.Div
      name="Test badge"
      style={{
        position: "absolute",
        left: 64,
        top: 120,
        padding: "8px 22px",
        borderRadius: 999,
        backgroundColor: "#EF4444",
        color: "#FFFFFF",
        fontFamily: HEADING_FONT,
        fontWeight: 700,
        fontSize: 30,
        letterSpacing: 2,
      }}
    >
      TEST · ทดสอบระบบ ห้ามเผยแพร่
    </Interactive.Div>
  );
};
