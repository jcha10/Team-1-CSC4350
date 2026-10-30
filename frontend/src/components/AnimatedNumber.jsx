import { useEffect } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";

/**
 * Smoothly tweens between successive numeric values instead of snapping,
 * so a stat that ticks up every simulator interval reads as "live" rather
 * than just re-rendering a new number.
 */
export default function AnimatedNumber({ value, decimals = 0 }) {
  const motionValue = useMotionValue(value);
  const rounded = useTransform(motionValue, (v) => v.toFixed(decimals));

  useEffect(() => {
    const controls = animate(motionValue, value, { duration: 0.6, ease: "easeOut" });
    return controls.stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <motion.span>{rounded}</motion.span>;
}
