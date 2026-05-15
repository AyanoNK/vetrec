import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderWithProviders, screen, userEvent } from "./test/utils";
import { server } from "./test/handlers";
import App from "./App";

describe("App", () => {
  it("renders the empty state on first render", () => {
    renderWithProviders(<App />);
    expect(screen.getByText(/paste a transcript/i)).toBeInTheDocument();
  });

  it("submits a transcript and renders the returned timeline", async () => {
    const user = userEvent.setup();
    renderWithProviders(<App />);

    await user.type(
      screen.getByRole("textbox", { name: /transcript/i }),
      "Bella presented for wellness exam."
    );
    await user.click(screen.getByRole("button", { name: /extract/i }));

    expect(
      await screen.findByText(/presenting complaint/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/maropitant/i)).toBeInTheDocument();
  });

  it("shows the timeout error when backend returns 504", async () => {
    server.use(
      http.post("/api/extract", () =>
        HttpResponse.json({ error: "llm_timeout" }, { status: 504 })
      )
    );
    const user = userEvent.setup();
    renderWithProviders(<App />);
    await user.type(
      screen.getByRole("textbox", { name: /transcript/i }),
      "anything"
    );
    await user.click(screen.getByRole("button", { name: /extract/i }));
    expect(await screen.findByText(/timed out/i)).toBeInTheDocument();
  });
});
