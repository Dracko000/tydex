import type { Metadata } from "next";
import { IBM_Plex_Sans, JetBrains_Mono } from "next/font/google";
import { MotionConfig } from "framer-motion";
import "./globals.css";

const plex = IBM_Plex_Sans({
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-plex",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-jb",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://dracko000.github.io/tydex/"),
  title: {
    default: "tydex — decisions as data, not prose",
    template: "%s · tydex",
  },
  description:
    "Typed decision primitives for LLMs — choice, score, noul — returned as JSON with calibrated probabilities and confidence. Python API, async FastAPI server, and escalation routing built in.",
  openGraph: {
    type: "website",
    url: "https://dracko000.github.io/tydex/",
    title: "tydex — decisions as data, not prose",
    description:
      "Choice, score, noul — returned as JSON with calibrated probabilities and confidence. Python API + async HTTP server.",
    images: [{ url: "/logo.svg", width: 1000, height: 1000, alt: "tydex logo" }],
  },
  twitter: {
    card: "summary",
    title: "tydex",
    description: "Typed decision primitives for LLMs — calibrated probabilities, not prose.",
    images: ["/logo.svg"],
  },
  icons: {
    icon: "/logo.svg",
    shortcut: "/logo.svg",
    apple: "/logo.svg",
  },
};

const themeScript = `(function(){try{var s=localStorage.getItem("theme");var d=s?(s==="dark"):(matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);}catch(e){}})();`;

export default function RootLayout(props: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${plex.variable} ${jetbrains.variable}`}
    >
      <body>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <MotionConfig reducedMotion="user">{props.children}</MotionConfig>
      </body>
    </html>
  );
}