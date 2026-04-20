import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

function getCookie(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1] ?? "";
}

export default function AuthPage({ initialMode = "login" }) {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const mode = initialMode;
  const [form, setForm] = useState({
    username: "",
    email: "",
    password1: "",
    password2: "",
    password: "",
  });

  useEffect(() => {
    fetch("/api/auth/status/", { credentials: "same-origin" }).catch(() => {});
  }, []);

  useEffect(() => {
    setStatus("idle");
    setMessage("");
  }, [mode]);

  const endpoint = useMemo(
    () => (mode === "login" ? "/api/auth/login/" : "/api/auth/register/"),
    [mode]
  );

  const submitLabel = mode === "login" ? "Login" : "Sign Up";

  const updateField = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("submitting");
    setMessage("");

    const payload =
      mode === "login"
        ? { username: form.username, password: form.password }
        : {
            username: form.username,
            email: form.email,
            password1: form.password1,
            password2: form.password2,
          };

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify(payload),
      });

      const contentType = response.headers.get("content-type");
      let data = {};
      
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        // Handle non-JSON response (e.g. 404, 500 HTML pages)
        if (!response.ok) {
          throw new Error(`Server error (${response.status}). Please ensure the backend is running.`);
        }
        throw new Error("Unexpected response from server.");
      }

      if (!response.ok) {
        let errMsg = data.error || data.detail || "Request failed.";
        if (data.errors) {
          const details = Object.entries(data.errors)
            .map(([field, errors]) => `${field}: ${errors.join(", ")}`)
            .join(" | ");
          errMsg += ` (${details})`;
        }
        throw new Error(errMsg);
      }

      setStatus("success");
      setMessage(data.message || `${submitLabel} successful.`);
    } catch (error) {
      setStatus("error");
      setMessage(error.message);
    }
  };

  return (
    <div className="auth-shell">
      <div className="glass auth-card">
        <div className="auth-header">
          <h1>{mode === "login" ? "Welcome back" : "Create Account"}</h1>
          <p>
            {mode === "login"
              ? "Sign in to continue into DarcOS."
              : "Get started with your new workspace."}
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Username
            <input type="text" value={form.username} onChange={updateField("username")} required />
          </label>

          {mode === "signup" && (
            <label>
              Email Address
              <input type="email" value={form.email} onChange={updateField("email")} required />
            </label>
          )}

          <label>
            Password
            <input
              type="password"
              value={mode === "login" ? form.password : form.password1}
              onChange={updateField(mode === "login" ? "password" : "password1")}
              required
            />
          </label>

          {mode === "signup" && (
            <label>
              Confirm Password
              <input type="password" value={form.password2} onChange={updateField("password2")} required />
            </label>
          )}

          <button type="submit" className="sim-button auth-submit" disabled={status === "submitting"}>
            {status === "submitting" ? "Processing..." : submitLabel}
          </button>
        </form>

        <p className="auth-footer">
          {mode === "login" ? (
            <>
              Need an account? <Link to="/signup">Sign up</Link>
            </>
          ) : (
            <>
              Already have an account? <Link to="/login">Login</Link>
            </>
          )}
        </p>

        {message && (
          <p className={`auth-status ${status === "error" ? "error" : "success"}`}>
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
