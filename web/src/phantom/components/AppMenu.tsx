import type { ReactNode } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import { usePhantom } from "../lib/store";
import type { Density, OverlayKind, WorkflowId } from "../lib/types";
import { WORKFLOW_ORDER, WORKFLOWS } from "../lib/workflows";
import { cn } from "../../lib/utils";
import { hasJamesHost, jamesBack, jamesOnline } from "../james-bridge";

export function AppMenu() {
  const density = usePhantom((s) => s.density);
  const setDensity = usePhantom((s) => s.setDensity);
  const setOverlay = usePhantom((s) => s.setOverlay);
  const openPoA = usePhantom((s) => s.openPoA);
  const runWorkflow = usePhantom((s) => s.runWorkflow);
  const workflow = usePhantom((s) => s.workflow);
  const poaOk = usePhantom((s) => s.poaOk);
  const poa = usePhantom((s) => s.poa);

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label="Utilities"
          className="inline-flex size-11 items-center justify-center rounded-md text-muted hover:bg-raised hover:text-fg"
        >
          <MoreHorizontal className="size-5" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={6} className="menu-surface">
          <Group label="Playbooks">
            {WORKFLOW_ORDER.map((id) => (
              <Item
                key={id}
                active={workflow === id}
                onSelect={() => void runWorkflow(id as WorkflowId)}
              >
                {WORKFLOWS[id].name}
              </Item>
            ))}
          </Group>
          <DropdownMenu.Separator className="my-2 h-px bg-line" />
          <Group label="Views">
            <Item onSelect={() => setOverlay("telemetry" as OverlayKind)}>Telemetry</Item>
            <Item onSelect={() => setOverlay("events")}>Audit log</Item>
            <Item onSelect={() => setOverlay("adapters")}>Radios</Item>
            <Item onSelect={() => setOverlay("report")}>Reports</Item>
          </Group>
          <DropdownMenu.Separator className="my-2 h-px bg-line" />
          <Group label="Density">
            {(["comfortable", "compact", "focus"] as Density[]).map((d) => (
              <Item key={d} active={density === d} onSelect={() => setDensity(d)}>
                {d[0]!.toUpperCase() + d.slice(1)}
              </Item>
            ))}
          </Group>
          <DropdownMenu.Separator className="my-2 h-px bg-line" />
          <Item onSelect={() => openPoA(true)}>{poaOk ? poa?.roe.engagementId ?? "Authorization" : "Authorization"}</Item>
          {hasJamesHost() ? (
            <>
              <DropdownMenu.Separator className="my-2 h-px bg-line" />
              <Group label="JAMES">
                <Item onSelect={() => jamesBack()}>Agent console</Item>
                <DropdownMenu.Label className="px-2 py-1 text-2xs text-muted">
                  Radios {jamesOnline() ? "live" : "offline"}
                </DropdownMenu.Label>
              </Group>
            </>
          ) : null}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <DropdownMenu.Group>
      <DropdownMenu.Label className="px-2 py-1 text-2xs font-medium tracking-wide text-muted uppercase">
        {label}
      </DropdownMenu.Label>
      {children}
    </DropdownMenu.Group>
  );
}

function Item({
  children,
  onSelect,
  active,
}: {
  children: ReactNode;
  onSelect: () => void;
  active?: boolean;
}) {
  return (
    <DropdownMenu.Item
      onSelect={onSelect}
      className={cn(
        "flex min-h-10 cursor-pointer items-center rounded-md px-2 text-sm text-fg outline-none",
        "data-[highlighted]:bg-raised",
        active && "text-accent",
      )}
    >
      {children}
    </DropdownMenu.Item>
  );
}
