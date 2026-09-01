import { useCallback, useEffect, useState } from "react";
import { usePhantom } from "../lib/store";
import { cn } from "../../lib/utils";
import { BootSequence } from "./BootSequence";
import { ConsoleDrawer } from "./ConsoleDrawer";
import { OverlayModals } from "./OverlayModals";
import { PoAOverlay } from "./PoAOverlay";
import { StatusPanel } from "./StatusPanel";
import { TargetList } from "./TargetList";
import { MobileStageNav, TopNavigation } from "./TopNavigation";
import { WorkflowWorkspace } from "./WorkflowWorkspace";

export function PhantomApp() {
  const boot = usePhantom((s) => s.boot);
  const booted = usePhantom((s) => s.booted);
  const density = usePhantom((s) => s.density);
  const stage = usePhantom((s) => s.stage);
  const setStage = usePhantom((s) => s.setStage);
  const [showBoot, setShowBoot] = useState(true);
  const [wide, setWide] = useState(true);
  const [xl, setXl] = useState(true);
  const [targetsOpen, setTargetsOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);

  useEffect(() => {
    const wq = window.matchMedia("(min-width: 960px)");
    const xq = window.matchMedia("(min-width: 1280px)");
    const apply = () => {
      setWide(wq.matches);
      setXl(xq.matches);
      if (wq.matches) setTargetsOpen(false);
      if (xq.matches) setStatusOpen(false);
    };
    apply();
    wq.addEventListener("change", apply);
    xq.addEventListener("change", apply);
    return () => {
      wq.removeEventListener("change", apply);
      xq.removeEventListener("change", apply);
    };
  }, []);

  const finishBoot = useCallback(() => {
    setShowBoot(false);
    if (!usePhantom.getState().booted) void usePhantom.getState().boot();
  }, []);

  useEffect(() => {
    if (!showBoot && !booted) void boot();
  }, [showBoot, booted, boot]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setTargetsOpen(false);
      setStatusOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (showBoot) return <BootSequence onDone={finishBoot} />;

  const dockLeft = density !== "focus" && wide;
  const dockRight = density !== "focus" && xl;
  const overlayLeft = density !== "focus" && !wide && targetsOpen;
  const overlayRight = density !== "focus" && !xl && statusOpen;

  return (
    <div
      data-density={density}
      className="app-shell flex h-dvh min-h-0 flex-col overflow-hidden bg-canvas text-fg"
    >
      <TopNavigation
        showTargetToggle={density !== "focus" && !wide}
        showStatusToggle={density !== "focus" && !xl}
        targetsOpen={targetsOpen}
        statusOpen={statusOpen}
        onTargets={() => {
          setTargetsOpen((v) => !v);
          setStatusOpen(false);
        }}
        onStatus={() => {
          setStatusOpen((v) => !v);
          setTargetsOpen(false);
        }}
      />
      <MobileStageNav stage={stage} onStage={setStage} />

      <div className="relative min-h-0 flex-1">
        <div
          className={cn(
            "grid h-full min-h-0",
            dockLeft && dockRight
              ? "grid-cols-[minmax(220px,22%)_minmax(0,1fr)_minmax(220px,25%)]"
              : dockLeft
                ? "grid-cols-[minmax(220px,280px)_minmax(0,1fr)]"
                : dockRight
                  ? "grid-cols-[minmax(0,1fr)_minmax(220px,280px)]"
                  : "grid-cols-1",
          )}
        >
          {dockLeft ? (
            <div className="min-h-0 min-w-0 border-r border-line">
              <TargetList />
            </div>
          ) : null}
          <div className="min-h-0 min-w-0">
            <WorkflowWorkspace />
          </div>
          {dockRight ? (
            <div className="min-h-0 min-w-0 border-l border-line">
              <StatusPanel />
            </div>
          ) : null}
        </div>

        {overlayLeft || overlayRight ? (
          <button
            type="button"
            aria-label="Dismiss panel"
            className="slide-scrim"
            onClick={() => {
              setTargetsOpen(false);
              setStatusOpen(false);
            }}
          />
        ) : null}
        {overlayLeft ? (
          <div className="slide-over slide-over-left">
            <TargetList />
          </div>
        ) : null}
        {overlayRight ? (
          <div className="slide-over slide-over-right">
            <StatusPanel />
          </div>
        ) : null}
      </div>

      <ConsoleDrawer />
      <PoAOverlay />
      <OverlayModals />
    </div>
  );
}
