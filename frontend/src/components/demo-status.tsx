// Demo-status popup: credit exhaustion and the settings showcase notice.
// Both are console-wide, so they live in the shell and render over any screen.

import { useState } from "react";
import { WarningIcon } from "@phosphor-icons/react/dist/csr/Warning";
import { XIcon } from "@phosphor-icons/react/dist/csr/X";
import { useCreditsExhausted } from "@/lib/store";

/** Modal shown when a call reports the voice provider ran out of credits. */
export function CreditsExhaustedBanner() {
  const credits = useCreditsExhausted();
  const [dismissed, setDismissed] = useState(false);
  if (!credits || dismissed) return null;
  return (
    <div
      role="alertdialog"
      aria-label="Demo finished"
      className="fixed inset-x-4 bottom-20 z-50 mx-auto max-w-md rounded-cards border border-line-2 bg-bg p-5 md:bottom-6"
    >
      <div className="flex items-start gap-3">
        <WarningIcon size={20} className="mt-0.5 shrink-0 text-fg-2" aria-hidden="true" />
        <div className="grid gap-1.5">
          <p className="text-[15px] text-fg">The demo has finished: credits are exhausted.</p>
          <p className="text-[13px] text-fg-2">
            The {credits.provider === "codex" ? "GPT-Live subscription" : "OpenAI account"} behind the voice agent has
            run out of credits, so new calls cannot start. Everything already recorded stays reviewable. Note: the
            phone line's own (Twilio) balance is not visible from this app, so it cannot be checked here.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
          className="ml-auto flex size-8 shrink-0 items-center justify-center rounded-tags text-fg-3 hover:text-fg"
        >
          <XIcon size={16} />
        </button>
      </div>
    </div>
  );
}
