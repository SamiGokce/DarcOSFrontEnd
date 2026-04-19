import { useEffect, useState } from "react";
import styles from "./Home.module.css";

export default function Home() {
  const [backendStatus, setBackendStatus] = useState("checking");

  useEffect(() => {
    const controller = new AbortController();

    fetch("/api/auth/status/", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend request failed.");
        }

        return response.json();
      })
      .then(() => setBackendStatus("connected"))
      .catch((error) => {
        if (error.name !== "AbortError") {
          setBackendStatus("disconnected");
        }
      });

    return () => controller.abort();
  }, []);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Welcome to DarcOS</h1>
      <p style={{ marginTop: "1rem", opacity: 0.8 }}>
        Elegant simplicity meets technical precision.
      </p>
      <p style={{ marginTop: "1.5rem", fontSize: "0.95rem", opacity: 0.75 }}>
        Django backend status: {backendStatus}
      </p>
    </div>
  );
}
