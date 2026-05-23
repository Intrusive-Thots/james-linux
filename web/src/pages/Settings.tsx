import { motion } from "framer-motion";
import { Wifi, Shield, Palette, Bell } from "lucide-react";

export function SettingsPage() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-y-auto p-lg"
    >
      <div className="max-w-dashboard mx-auto space-y-lg">
        <div>
          <h2 className="text-h2 text-text-primary mb-[2px]">Settings</h2>
          <p className="text-body text-text-secondary">
            Configure JAMES agent preferences and defaults.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-lg">
          <SettingsCard
            icon={Wifi}
            title="Wireless"
            items={[
              { label: "Default interface", value: "wlan0" },
              { label: "Recon duration", value: "20 seconds" },
              { label: "Deauth attempts", value: "3" },
            ]}
          />
          <SettingsCard
            icon={Shield}
            title="Attack Engine"
            items={[
              { label: "Auto-crack", value: "Enabled" },
              { label: "Default wordlist", value: "rockyou.txt" },
              { label: "Evil Twin timeout", value: "10 min" },
            ]}
          />
          <SettingsCard
            icon={Palette}
            title="Interface"
            items={[
              { label: "Theme", value: "Dark Tactical" },
              { label: "Animations", value: "Enabled" },
              { label: "Log retention", value: "500 entries" },
            ]}
          />
          <SettingsCard
            icon={Bell}
            title="Notifications"
            items={[
              { label: "Sound alerts", value: "Disabled" },
              { label: "Desktop notifications", value: "Enabled" },
              { label: "Auto-report", value: "Enabled" },
            ]}
          />
        </div>
      </div>
    </motion.div>
  );
}

function SettingsCard({
  icon: Icon,
  title,
  items,
}: {
  icon: React.ElementType;
  title: string;
  items: { label: string; value: string }[];
}) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <Icon className="w-5 h-5 text-accent-cyan" />
          {title}
        </div>
      </div>
      <div className="space-y-md">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-body text-text-secondary">{item.label}</span>
            <span className="text-body text-text-primary font-medium">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
