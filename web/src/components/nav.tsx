"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import logo from "@images/logo.svg";
import { GithubIcon, LinkedinIcon, MenuIcon, XIcon } from "@/components/icons";
import { ThemeToggle } from "@/components/theme-toggle";
import { LINKS } from "@/lib/data";

const NAV = [
  { href: "#primitives", label: "Primitives" },
  { href: "#calibration", label: "Calibration" },
  { href: "#architecture", label: "Architecture" },
  { href: "#install", label: "Install" },
];

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-40 transition-all duration-300 ${
        scrolled
          ? "border-b border-line/70 bg-bg/85 backdrop-blur-md"
          : "border-b border-transparent bg-transparent"
      }`}
    >
      <nav
        aria-label="Main"
        className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6"
      >
        <a href="#top" className="flex items-center gap-2.5 no-underline">
          <Image
            src={logo}
            alt="tydex logo"
            width={28}
            height={28}
            className="h-7 w-7"
          />
          <span className="font-mono text-lg font-semibold tracking-tight text-ink">
            tydex
          </span>
        </a>

        <div className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-mut transition-colors duration-200 hover:bg-raise hover:text-ink"
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          <a
            href={LINKS.docs}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl px-3.5 py-2 text-sm font-medium text-mut transition-colors duration-200 hover:text-brand"
          >
            Docs
          </a>
          <a
            href={LINKS.github}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub repository"
            className="flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-surface text-mut transition-colors duration-200 hover:text-brand"
          >
            <GithubIcon className="h-5 w-5" />
          </a>
          <a
            href={LINKS.linkedin}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="AIMB X Labs on LinkedIn"
            className="flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-surface text-mut transition-colors duration-200 hover:text-brand"
          >
            <LinkedinIcon className="h-5 w-5" />
          </a>
          <ThemeToggle />
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-xl border border-line bg-surface text-ink"
          >
            {open ? <XIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
          </button>
        </div>
      </nav>

      {open ? (
        <div className="border-t border-line bg-bg/95 backdrop-blur-md md:hidden">
          <div className="mx-auto max-w-7xl space-y-1 px-4 py-3">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink"
              >
                {item.label}
              </a>
            ))}
            <a
              href={LINKS.docs}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink"
            >
              Docs
            </a>
          </div>
        </div>
      ) : null}
    </header>
  );
}