export function SectionDivider() {
  return (
    <div
      className="mx-auto my-20 flex w-full max-w-6xl items-center gap-4 px-6 md:px-8"
      aria-hidden
    >
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-nexus-border to-transparent" />
      <div className="h-1 w-1 rounded-full bg-nexus-accent/50" />
      <div className="h-px flex-1 bg-gradient-to-l from-transparent via-nexus-border to-transparent" />
    </div>
  );
}
