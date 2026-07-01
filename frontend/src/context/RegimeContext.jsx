import { createContext, useContext, useState, useMemo } from "react";

const REGIME_COLORS = {
  bull: {
    accent: "#10b981",     // emerald
    accentRgb: "16,185,129",
    secondary: "#4F8CFF",  // brand blue
    secondaryRgb: "79,140,255",
    label: "BULL",
  },
  sideways: {
    accent: "#f59e0b",     // amber
    accentRgb: "245,158,11",
    secondary: "#71717a",  // zinc
    secondaryRgb: "113,113,122",
    label: "SIDEWAYS",
  },
  bear: {
    accent: "#ef4444",     // red
    accentRgb: "239,68,68",
    secondary: "#f59e0b",  // amber
    secondaryRgb: "245,158,11",
    label: "BEAR",
  },
};

const RegimeContext = createContext({
  regime: "bull",
  setRegime: () => {},
  colors: REGIME_COLORS.bull,
});

export function RegimeProvider({ children }) {
  const [regime, setRegime] = useState("bull");
  const colors = useMemo(() => REGIME_COLORS[regime], [regime]);
  return (
    <RegimeContext.Provider value={{ regime, setRegime, colors }}>
      {children}
    </RegimeContext.Provider>
  );
}

export function useRegime() {
  return useContext(RegimeContext);
}
