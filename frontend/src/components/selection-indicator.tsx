import { useCallback, useLayoutEffect, useRef } from "react";

/** One background moves between the selected controls; labels stay stationary. */
export function SelectionIndicator({ activeKey, className = "" }: { activeKey: string; className?: string }) {
  const indicator = useRef<HTMLSpanElement>(null);
  const initialized = useRef(false);
  const position = useCallback((animate: boolean) => {
    const el = indicator.current;
    const selected = el?.parentElement?.querySelector<HTMLElement>('[aria-current="page"], [aria-selected="true"], [aria-pressed="true"]');
    if (!el || !selected) return;
    el.style.transition = animate && initialized.current ? "" : "none";
    el.style.transform = `translate(${selected.offsetLeft}px, ${selected.offsetTop}px)`;
    el.style.width = `${selected.offsetWidth}px`;
    el.style.height = `${selected.offsetHeight}px`;
    initialized.current = true;
  }, []);
  useLayoutEffect(() => {
    const parent = indicator.current?.parentElement;
    if (!parent) return;
    const observer = new ResizeObserver(() => position(false));
    observer.observe(parent);
    // Fonts and labels can resize controls without changing the track's size.
    for (const control of parent.children) {
      if (control !== indicator.current) observer.observe(control);
    }
    return () => observer.disconnect();
  }, [position]);
  useLayoutEffect(() => position(true), [activeKey, position]);
  return <span ref={indicator} className={`selection-indicator ${className}`} aria-hidden="true" />;
}
