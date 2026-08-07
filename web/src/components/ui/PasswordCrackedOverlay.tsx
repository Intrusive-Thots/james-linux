import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { Unlock, Copy, Check, X, ShieldAlert } from "lucide-react";

interface PasswordCrackedOverlayProps {
  show: boolean;
  password?: string;
  essid?: string;
  onClose: () => void;
}

export function PasswordCrackedOverlay({
  show,
  password = "",
  essid = "Target Network",
  onClose,
}: PasswordCrackedOverlayProps) {
  const [copied, setCopied] = useState(false);
  const [scramble, setScramble] = useState("");

  // Hacker text scrambling effect for the password
  useEffect(() => {
    if (!show || !password) return;

    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()";
    let iterations = 0;
    const maxIterations = 20;
    
    const interval = setInterval(() => {
      setScramble(
        password
          .split("")
          .map((char, index) => {
            if (index < iterations / (maxIterations / password.length)) {
              return char;
            }
            return chars[Math.floor(Math.random() * chars.length)];
          })
          .join("")
      );
      
      iterations++;
      if (iterations >= maxIterations) {
        clearInterval(interval);
        setScramble(password);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [show, password]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && show) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [show, onClose]);

  const handleCopy = () => {
    if (password) {
      navigator.clipboard.writeText(password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center overflow-hidden bg-black/90 backdrop-blur-xl"
        >
          {/* Animated Background Gradients */}
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1.5, opacity: 0.15 }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            className="absolute w-[800px] h-[800px] bg-success rounded-full blur-[120px] pointer-events-none"
          />

          <button
            onClick={onClose}
            className="absolute top-6 right-6 p-3 text-text-muted hover:text-white transition-colors z-50 rounded-full hover:bg-white/10"
          >
            <X className="w-8 h-8" />
          </button>

          <motion.div
            initial={{ scale: 0.8, y: 50, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            transition={{ type: "spring", damping: 20, stiffness: 100, delay: 0.2 }}
            className="relative w-full max-w-3xl p-8"
          >
            <div className="flex flex-col items-center text-center space-y-8">
              
              <motion.div
                initial={{ rotate: -180, scale: 0 }}
                animate={{ rotate: 0, scale: 1 }}
                transition={{ type: "spring", damping: 15, delay: 0.4 }}
                className="w-32 h-32 rounded-full bg-success/20 border-2 border-success/50 flex items-center justify-center shadow-[0_0_50px_rgba(16,185,129,0.4)] relative"
              >
                <div className="absolute inset-0 rounded-full border border-success animate-ping opacity-20" />
                <Unlock className="w-16 h-16 text-success" />
              </motion.div>

              <div className="space-y-2">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.6 }}
                  className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-success/10 border border-success/30 text-success text-sm font-bold tracking-widest uppercase mb-4"
                >
                  <ShieldAlert className="w-4 h-4" />
                  System Compromised
                </motion.div>
                
                <motion.h1
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                  className="text-5xl md:text-7xl font-black text-white tracking-tight"
                >
                  ACCESS <span className="text-transparent bg-clip-text bg-gradient-to-r from-success to-emerald-300">GRANTED</span>
                </motion.h1>
                
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.9 }}
                  className="text-xl text-text-secondary mt-4 font-mono"
                >
                  Network <span className="text-white font-bold">{essid}</span> has been decrypted.
                </motion.p>
              </div>

              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 1.2, type: "spring" }}
                className="w-full max-w-xl relative mt-8 group"
              >
                <div className="absolute -inset-1 bg-gradient-to-r from-success/50 to-emerald-500/50 rounded-xl blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200" />
                <div className="relative bg-black/80 border border-success/50 rounded-xl p-8 font-mono flex flex-col items-center justify-center">
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-black px-4 text-xs font-bold text-success uppercase tracking-widest border border-success/30 rounded-full">
                    WPA-PSK Password
                  </div>
                  
                  <div className="text-4xl md:text-5xl font-bold text-white tracking-widest py-4 select-all break-all text-center">
                    {scramble || "•".repeat(password?.length || 8)}
                  </div>
                  
                  <button
                    onClick={handleCopy}
                    className="absolute bottom-4 right-4 p-3 bg-success/20 hover:bg-success/30 text-success rounded-lg transition-colors flex items-center gap-2 font-bold text-sm border border-success/30 hover:border-success/60 hover:shadow-[0_0_15px_rgba(16,185,129,0.4)]"
                  >
                    {copied ? (
                      <>
                        <Check className="w-5 h-5" />
                        COPIED
                      </>
                    ) : (
                      <>
                        <Copy className="w-5 h-5" />
                        COPY KEY
                      </>
                    )}
                  </button>
                </div>
              </motion.div>

              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
                onClick={onClose}
                className="text-text-muted hover:text-white underline underline-offset-4 mt-8 transition-colors"
              >
                Close and return to dashboard
              </motion.button>
              
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
