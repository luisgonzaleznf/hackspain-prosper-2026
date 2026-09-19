// ROSARIO design-lint: an ESLint-compatible plugin run by Oxlint (jsPlugins).
// It guards the rules in frontend/DESIGN.md inside TS/TSX source: colors and
// fonts come from tokens, motion never loops, no decorative chrome, no em dashes.
// CSS files are covered separately by Stylelint (see frontend/.stylelintrc.json).
//
// Every rule scans string-bearing nodes (Literal, TemplateLiteral quasis,
// JSXText) so it catches className strings, cva() variants, inline style
// objects and copy alike. Keep the patterns simple and the messages actionable.

/** Regexes that identify raw colors anywhere in a string. */
const RAW_COLOR = [
  // Hex, but not inside a URL hash fragment (#/path) or a JSX id (#root).
  /(?<![\w/&])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/,
  /\b(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\(/,
  // Tailwind default palette: bg-zinc-800, text-red-500, border-slate-700/50 ...
  /\b(?:bg|text|border|ring|fill|stroke|from|via|to|outline|decoration|divide|accent|caret|shadow|placeholder)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/,
  // Tailwind literal black/white utilities. Use token utilities instead.
  /\b(?:bg|text|border|ring|fill|stroke|from|via|to)-(?:white|black)\b/,
  // Tailwind arbitrary color values: bg-[#000], text-[rgb(...)].
  /\b(?:bg|text|border|ring|fill|stroke|from|via|to)-\[(?:#|rgb|hsl|oklch)/,
];

/** Tailwind classes and CSS fragments that repaint forever. */
const INFINITE_MOTION = [
  /\banimate-(?:spin|ping|pulse|bounce)\b/,
  /(?<!no-)\binfinite\b/,
  /\brepeat\s*:\s*Infinity\b/,
];

/** Decorative chrome the style forbids: shadows, blur, gradients on surfaces, oversized radii. */
const DECORATIVE_CHROME = [
  /\b(?:shadow-(?:2xs|xs|sm|md|lg|xl|2xl|inner)|drop-shadow(?:-\w+)?)\b/,
  /\bblur-(?:xs|sm|md|lg|xl|2xl|3xl)\b/,
  /\bbg-(?:linear|radial|conic|gradient)-/,
  /\brounded-4xl\b/,
];

/** Fonts must come from the tokens (font-sans, font-mono, font-display). */
const RAW_FONT = [
  /\bfont-\[/,
  /\bfont-(?:serif)\b/,
  /font-family\s*:\s*(?!var\()/,
];

const EM_DASH = /—/;

/**
 * Iterate the plain-text pieces of a node: string Literal values, each quasi
 * of a TemplateLiteral, and JSX text. Returns [] for other node kinds.
 */
function textsOf(node) {
  if (node.type === "Literal") return typeof node.value === "string" ? [node.value] : [];
  if (node.type === "TemplateLiteral") return node.quasis.map((q) => q.value.cooked ?? q.value.raw);
  if (node.type === "JSXText") return [node.value];
  return [];
}

/** Build a rule that reports when any pattern matches any text piece of a node. */
function textRule(description, patterns, message) {
  return {
    meta: {
      type: "problem",
      docs: { description },
      messages: { violation: message },
    },
    create(context) {
      const check = (node) => {
        for (const text of textsOf(node)) {
          const hit = patterns.find((re) => re.test(text));
          if (hit) {
            context.report({ node, messageId: "violation", data: { match: text.match(hit)[0] } });
            return;
          }
        }
      };
      return { Literal: check, TemplateLiteral: check, JSXText: check };
    },
  };
}

/**
 * Inline style objects: `style={{ fontFamily: "Inter" }}`, `color: "#fff"`.
 * Property keys that carry color, font or animation are checked at the key
 * level so the message can name the CSS property.
 */
const noInlineStyleTokens = {
  meta: {
    type: "problem",
    docs: { description: "Inline style values for color, font and animation must reference CSS variables or be removed." },
    messages: {
      violation: "Inline style `{{prop}}` must use var(--token) (found `{{value}}`). Prefer a className bound to tokens.",
    },
  },
  create(context) {
    const GUARDED = /^(?:color|background(?:Color)?|border(?:Color)?|outline(?:Color)?|fill|stroke|fontFamily|boxShadow|animation(?:IterationCount)?)$/;
    return {
      Property(node) {
        const key = node.key.type === "Identifier" ? node.key.name : node.key.type === "Literal" ? String(node.key.value) : null;
        if (!key || !GUARDED.test(key)) return;
        // Element.animate() options use `fill` for playback behavior, not SVG color.
        const object = node.parent;
        const call = object?.parent;
        if (key === "fill" && call?.type === "CallExpression" && call.arguments[1] === object &&
          call.callee.type === "MemberExpression" && !call.callee.computed &&
          call.callee.property.type === "Identifier" && call.callee.property.name === "animate") return;
        const texts = textsOf(node.value);
        if (texts.length === 0) return;
        const value = texts.join("");
        if (/^\s*var\(--/.test(value) || /^(?:none|transparent|inherit|currentColor)$/.test(value.trim())) return;
        context.report({ node: node.value, messageId: "violation", data: { prop: key, value } });
      },
    };
  },
};

const plugin = {
  meta: { name: "design", version: "0.1.0" },
  rules: {
    "no-raw-color": textRule(
      "Colors must come from design tokens; no hex, rgb(), hsl() or Tailwind palette classes in source.",
      RAW_COLOR,
      "Raw color `{{match}}`. Use a token utility (bg-background, text-foreground, bg-accent...) or var(--token).",
    ),
    "no-infinite-motion": textRule(
      "No continuously repainting animation: no animate-spin/pulse/ping/bounce, no `infinite`, no repeat: Infinity.",
      INFINITE_MOTION,
      "Looping animation `{{match}}` pegs the GPU on high-refresh displays. Use a one-shot 150 to 300ms transition, or drive motion from real audio levels.",
    ),
    "no-decorative-chrome": textRule(
      "No ad-hoc shadows, blur or gradients; use the glow, gradient and radius tokens from tokens.css.",
      DECORATIVE_CHROME,
      "Chrome `{{match}}` is not a token. Use the glow-*, gradient-* and radius-* tokens from tokens.css.",
    ),
    "no-raw-font": textRule(
      "Fonts come from the three token families: font-sans, font-mono, font-display.",
      RAW_FONT,
      "Raw font `{{match}}`. Use font-sans, font-mono or font-display.",
    ),
    "no-em-dash": textRule(
      "No em dashes in copy or code strings.",
      [EM_DASH],
      "Em dash in text. Use a hyphen, a colon, or split the sentence.",
    ),
    "no-inline-style-tokens": noInlineStyleTokens,
  },
};

export default plugin;
