/**
 * Skeleton placeholders for the first menu fetch. Shapes match the real hero,
 * category rail, and card grid so the page does not jump when data arrives.
 */
export function MenuSkeleton() {
  return (
    <div className="m-skeleton-wrap" role="status" aria-live="polite" aria-busy="true">
      <span className="visually-hidden">Loading the menu…</span>

      <div className="m-skel m-skel-hero" aria-hidden="true" />

      <div className="m-skel-chips" aria-hidden="true">
        <span className="m-skel m-skel-chip" />
        <span className="m-skel m-skel-chip" />
        <span className="m-skel m-skel-chip" />
        <span className="m-skel m-skel-chip" />
      </div>

      <div className="m-skel-grid" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => (
          <div className="m-skel-card" key={index}>
            <div className="m-skel m-skel-photo" />
            <div className="m-skel-card-body">
              <div className="m-skel m-skel-line w-60" />
              <div className="m-skel m-skel-line w-80" />
              <div className="m-skel m-skel-line w-40" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
