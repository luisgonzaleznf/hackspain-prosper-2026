export function Good({ level }: { level: number }) {
  return (
    <div className="bg-background text-foreground border-hairline rounded-control" style={{ color: "var(--accent-ink)", transform: `scale(${1 + level})` }}>
      Hello, world. See #/calls/123
    </div>
  );
}

export function reveal(element: HTMLElement) {
  return element.animate({ opacity: [0, 1] }, { duration: 250, fill: "forwards" });
}
