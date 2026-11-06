import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { platformFetch } from "../../lib/platformApi";

export default function RegisterSuccessPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [registration, setRegistration] = useState<{
    id: string;
    status: string;
    restaurant_id: string | null;
    owner_email: string | null;
    invitation_token: string | null;
    invitation_expires_at: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const registrationId = searchParams.get("registration_id");
    const token = searchParams.get("token");
    const restaurantId = searchParams.get("restaurant");

    if (token && restaurantId) {
      // Direct invitation - show success with token
      setRegistration({
        id: registrationId || "",
        status: "APPROVED",
        restaurant_id: restaurantId,
        owner_email: "",
        invitation_token: token,
        invitation_expires_at: "",
      });
      setLoading(false);
      return;
    }

    if (registrationId) {
      async function loadRegistration() {
        try {
          const res = await platformFetch(
            `/api/platform/self-service/registrations/${registrationId}`
          );
          if (!res.ok) throw new Error("Failed to load registration");
          const data = await res.json();
          setRegistration(data);
        } catch (err: any) {
          console.error("Failed to load registration:", err);
        } finally {
          setLoading(false);
        }
      }
      loadRegistration();
    } else {
      setLoading(false);
    }
  }, [searchParams]);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 600 }}>
        <h1 style={{ marginTop: 0 }}>Registration Submitted</h1>
        <p>Processing...</p>
      </div>
    );
  }

  if (!registration) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 600 }}>
        <h1 style={{ marginTop: 0 }}>Registration Submitted</h1>
        <p>No registration information found.</p>
        <button
          onClick={() => window.location.href = "/admin/plans"}
          className="pf-button secondary"
        >
          Back to Plans
        </button>
      </div>
    );
  }

  const isApproved = registration.status === "APPROVED";

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 600 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 24,
            background: isApproved ? "#e7f4ea" : "#fff4e5",
            color: isApproved ? "#17643b" : "#9a6200",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 24,
          }}
        >
          {isApproved ? "✓" : "⏳"}
        </div>
        <div>
          <h1 style={{ margin: 0 }}>
            {isApproved ? "Registration Approved!" : "Registration Submitted"}
          </h1>
          <p className="pf-muted" style={{ margin: "4px 0 0 0" }}>
            {isApproved
              ? "Your restaurant has been registered and is ready for setup."
              : "Your registration has been submitted and is pending approval."}
          </p>
        </div>
      </div>

      <div style={{ marginBottom: 24, border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#f5f6f8" }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Registration Details</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#5b6678" }}>Status</span>
            <span
              style={{
                padding: "4px 8px",
                borderRadius: 4,
                background: registration.status === "APPROVED" ? "#e7f4ea" : "#fff4e5",
                color: registration.status === "APPROVED" ? "#17643b" : "#9a6200",
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {registration.status}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#5b6678" }}>Restaurant ID</span>
            <span style={{ fontFamily: "monospace", fontSize: 12 }}>{registration.restaurant_id}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#5b6678" }}>Owner Email</span>
            <span>{registration.owner_email}</span>
          </div>
          {registration.invitation_token && (
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
              <span style={{ color: "#5b6678" }}>Invitation Token</span>
              <span style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all" }}>
                {registration.invitation_token}
              </span>
            </div>
          )}
        </div>
      </div>

      {isApproved ? (
        <div style={{ display: "flex", gap: 8, flexDirection: "column" }}>
          <button
            onClick={() => {
              window.location.href = `/admin/login?invite=${registration.invitation_token}`;
            }}
            className="pf-button"
          >
            Complete Registration
          </button>
          <button
            onClick={() => window.location.href = "/admin/plans"}
            className="pf-button secondary"
          >
            Browse Plans
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", gap: 8, flexDirection: "column" }}>
          <button
            onClick={() => window.location.href = "/admin/plans"}
            className="pf-button"
          >
            Browse Plans
          </button>
        </div>
      )}

      <div style={{ marginTop: 24, borderTop: "1px solid #d9dde5", paddingTop: 16 }}>
        <h3 style={{ margin: "0 0 8px 0", fontSize: 14 }}>What happens next?</h3>
        <ul style={{ margin: 0, paddingLeft: 20, color: "#5b6678", fontSize: 13 }}>
          {isApproved ? (
            <>
              <li>Use the invitation link to complete your account setup</li>
              <li>Set your password and complete profile</li>
              <li>Start configuring your restaurant</li>
            </>
          ) : (
            <>
              <li>Our team will review your application</li>
              <li>You will receive an email when approved</li>
              <li>Once approved, you can complete your registration</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
}