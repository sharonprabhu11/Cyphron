<<<<<<< HEAD
"use client";

export default function HomePage() {
  console.log("Frontend running");

  return (
    <main style={{ padding: 24 }}>
      <h1 style={{ margin: 0, fontSize: 28 }}>Cyphron Dashboard Running</h1>
      <p style={{ marginTop: 12, opacity: 0.8 }}>
        This is the foundation UI scaffold. Business logic will be added later.
      </p>
    </main>
  );
}

=======
import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/dashboard");
}
>>>>>>> pr-7
