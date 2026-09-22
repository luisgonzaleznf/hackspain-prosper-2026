// 404: unknown console route. Says what was not found and offers the way back;
// it never silently redirects, so a mistyped call id is visible as a mistake.

import { ArrowLeftIcon } from "@phosphor-icons/react/dist/csr/ArrowLeft";
import { Link, useParams } from "react-router";
import { ScreenHeader } from "@/app";
import { Label, Mono } from "@/components/primitives";

export function NotFoundScreen() {
  const { "*": rest } = useParams();
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <ScreenHeader title="Not found" />
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 pb-24 text-center">
        <Mono className="text-fg-3" dim>
          404
        </Mono>
        <p className="max-w-md text-[14px] text-fg-2">
          There is no screen at <Mono>{rest || "this address"}</Mono>. Calls, calendar and
          settings live in the rail; a mistyped call id will not open.
        </p>
        <Link
          to="/metrics"
          className="inline-flex min-h-[44px] items-center gap-2 text-[14px] text-fg underline-offset-4 hover:underline"
        >
          <ArrowLeftIcon className="size-4" />
          Back to overview
        </Link>
        <Label className="mt-2">rosario console</Label>
      </div>
    </div>
  );
}
