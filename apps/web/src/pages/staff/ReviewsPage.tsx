import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  apiFetch,
  type Review,
  type ReviewsSummary,
} from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../lib/auth";

export default function ReviewsPage() {
  const { has } = useAuth();
  const canCreate = has("reviews.create");
  const canRespond = has("reviews.respond");
  const [summary, setSummary] = useState<ReviewsSummary | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [draft, setDraft] = useState({ rating: 5, title: "", content: "" });
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const query = statusFilter ? `?status=${statusFilter}` : "";
    const [summaryData, reviewList] = await Promise.all([
      apiFetch<ReviewsSummary>("/api/v1/reviews/summary"),
      apiFetch<Review[]>(`/api/v1/reviews${query}`),
    ]);
    setSummary(summaryData);
    setReviews(reviewList);
  }, [statusFilter]);

  useEffect(() => {
    void load().catch((err) =>
      setError(err instanceof ApiError ? err.detail : "Could not load reviews.")
    );
  }, [load]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The review action failed.");
    } finally {
      setBusy(false);
    }
  }

  function createReview() {
    return run(async () => {
      await apiFetch<Review>("/api/v1/reviews", {
        method: "POST",
        body: JSON.stringify({
          rating: draft.rating,
          title: draft.title.trim() || null,
          content: draft.content.trim() || null,
        }),
      });
      setDraft({ rating: 5, title: "", content: "" });
      return "Review recorded.";
    });
  }

  function respond(review: Review) {
    const text = (responses[review.id] ?? "").trim();
    if (!text) return Promise.resolve();
    return run(async () => {
      await apiFetch<Review>(`/api/v1/reviews/${review.id}/respond`, {
        method: "POST",
        body: JSON.stringify({ response_text: text }),
      });
      setResponses((current) => ({ ...current, [review.id]: "" }));
      return "Response published.";
    });
  }

  function setStatus(review: Review, status: string) {
    return run(async () => {
      await apiFetch<Review>(`/api/v1/reviews/${review.id}/status?status=${status}`, {
        method: "PATCH",
      });
      return `Review marked ${status.toLowerCase()}.`;
    });
  }

  const distribution = Object.entries(summary?.rating_distribution ?? {}).sort(
    (a, b) => Number(b[0]) - Number(a[0])
  );

  return (
    <div className="page">
      <PageHeader
        eyebrow="Guest feedback"
        title="Reviews"
        sub="Ratings are stored against the restaurant. Responses are appended to a separate record, so the original review is never overwritten."
        actions={
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">All statuses</option>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      {summary ? (
        <section className="report-grid" aria-label="Review summary">
          <article className="report-card">
            <p className="muted">Average rating</p>
            <p className="stat">{summary.average_rating.toFixed(2)}</p>
            <p className="kpi-foot">Across all reviews</p>
          </article>
          <article className="report-card">
            <p className="muted">Total reviews</p>
            <p className="stat">{summary.total_reviews}</p>
            <p className="kpi-foot">Restaurant-wide</p>
          </article>
          <article className="report-card">
            <p className="muted">Distribution</p>
            <p className="stat">
              {distribution.length === 0
                ? "—"
                : distribution.map(([rating, count]) => `${rating}★ ${count}`).join(" · ")}
            </p>
            <p className="kpi-foot">Ratings 1–5</p>
          </article>
        </section>
      ) : null}

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="reviews-list-title">
          <div className="section-card-head">
            <h3 id="reviews-list-title">Reviews</h3>
            <span className="muted text-sm">{reviews.length} shown</span>
          </div>
          <div className="section-card-body">
            {reviews.length === 0 ? <p className="muted">No reviews for this filter.</p> : null}
            {reviews.map((review) => (
              <article className="card method-card" key={review.id}>
                <div className="row">
                  <div>
                    <strong>{"★".repeat(review.rating)}</strong>
                    <span className="muted text-sm"> {review.title || "Untitled"}</span>
                  </div>
                  <span
                    className={`badge ${
                      review.status === "APPROVED"
                        ? "new"
                        : review.status === "REJECTED"
                          ? "rejected"
                          : "pending"
                    }`}
                  >
                    {review.status}
                  </span>
                </div>
                {review.content ? <p>{review.content}</p> : null}
                <p className="muted text-sm">
                  {new Date(review.created_at).toLocaleString()}
                  {review.responded_at
                    ? ` · responded ${new Date(review.responded_at).toLocaleString()}`
                    : ""}
                </p>
                {review.response_text ? (
                  <div className="notice">Response: {review.response_text}</div>
                ) : canRespond ? (
                  <form
                    className="stack"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void respond(review);
                    }}
                  >
                    <label className="field">
                      Reply
                      <textarea
                        rows={2}
                        value={responses[review.id] ?? ""}
                        onChange={(event) =>
                          setResponses((current) => ({
                            ...current,
                            [review.id]: event.target.value,
                          }))
                        }
                        placeholder="Thank the guest or explain the fix"
                      />
                    </label>
                    <div className="page-actions">
                      <button
                        className="btn btn-sm"
                        type="submit"
                        disabled={busy || !(responses[review.id] ?? "").trim()}
                      >
                        Publish response
                      </button>
                      {review.status !== "APPROVED" ? (
                        <button
                          className="btn ghost btn-sm"
                          type="button"
                          disabled={busy}
                          onClick={() => void setStatus(review, "APPROVED")}
                        >
                          Approve
                        </button>
                      ) : null}
                      {review.status !== "REJECTED" ? (
                        <button
                          className="btn ghost danger btn-sm"
                          type="button"
                          disabled={busy}
                          onClick={() => void setStatus(review, "REJECTED")}
                        >
                          Reject
                        </button>
                      ) : null}
                    </div>
                  </form>
                ) : (
                  <p className="muted text-sm">No response yet.</p>
                )}
              </article>
            ))}
          </div>
        </section>

        {canCreate ? (
          <section className="section-card" aria-labelledby="new-review-title">
          <div className="section-card-head">
            <h3 id="new-review-title">Record a review</h3>
          </div>
          <div className="section-card-body">
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void createReview();
              }}
            >
              <label className="field">
                Rating
                <select
                  value={draft.rating}
                  onChange={(event) => setDraft({ ...draft, rating: Number(event.target.value) })}
                >
                  {[5, 4, 3, 2, 1].map((value) => (
                    <option key={value} value={value}>
                      {value} star{value === 1 ? "" : "s"}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Title
                <input
                  value={draft.title}
                  onChange={(event) => setDraft({ ...draft, title: event.target.value })}
                />
              </label>
              <label className="field">
                Review
                <textarea
                  rows={4}
                  value={draft.content}
                  onChange={(event) => setDraft({ ...draft, content: event.target.value })}
                />
              </label>
              <button className="btn" type="submit" disabled={busy}>
                Record review
              </button>
            </form>
          </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
