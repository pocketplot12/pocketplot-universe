"""
PocketPlot Universe - branching story SVG.

An animated SVG that shows what PocketPlot does at a glance.

Visual concept:
  - A story tree (single starting node)
  - 3 branches going to 3 different scenes
  - Multiple paths through those scenes
  - Active path glows gently (it's a story being read)
  - Loops every 6 seconds

Animation: subtle, looping. No aggressive movement.

Colors: brass + cream + navy (matches the warm-light + warm-dark themes)
"""

BRANCHING_SVG = '''<svg class="branching-illustration reveal" viewBox="0 0 600 320" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Branching story paths">
  <defs>
    <linearGradient id="path-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="currentColor" stop-opacity="0.3" />
      <stop offset="50%" stop-color="currentColor" stop-opacity="1" />
      <stop offset="100%" stop-color="currentColor" stop-opacity="0.3" />
    </linearGradient>
  </defs>

  <style>
    /* Theme-aware: works with CSS color via currentColor */
    .branching-illustration {
      color: var(--brand, #c9a04e);
      max-width: 100%;
      height: auto;
    }

    /* Node styling */
    .node {
      fill: var(--bg-elevated, #15243f);
      stroke: currentColor;
      stroke-width: 1.5;
      transition: all 0.6s ease;
    }
    .node-start {
      fill: currentColor;
      stroke: currentColor;
      r: 7;
    }
    .node-circle {
      transition: r 0.6s ease, fill 0.6s ease, stroke-width 0.6s ease;
    }

    /* Connection paths */
    .path {
      stroke: currentColor;
      stroke-width: 1.2;
      fill: none;
      opacity: 0.35;
      stroke-dasharray: 4 4;
      stroke-linecap: round;
    }
    .path-active {
      opacity: 1;
      stroke-width: 2;
      stroke-dasharray: 200;
      stroke-dashoffset: 200;
      animation: drawPath 6s var(--ease-in-out, ease) infinite;
    }
    @keyframes drawPath {
      0% { stroke-dashoffset: 200; opacity: 1; }
      70% { stroke-dashoffset: 0; opacity: 1; }
      100% { stroke-dashoffset: -200; opacity: 0.3; }
    }

    /* Labels */
    .label {
      font-family: var(--font-serif, Georgia, serif);
      font-style: italic;
      font-size: 13px;
      fill: var(--text-body, #d8cba8);
      text-anchor: middle;
      transition: opacity 0.4s ease;
    }
    .label-eyebrow {
      font-family: var(--font-ui, Inter, sans-serif);
      font-size: 10px;
      letter-spacing: 0.15em;
      fill: var(--text-caption, #9eb6d4);
      text-anchor: middle;
      text-transform: uppercase;
    }

    /* Node active state - pulsing */
    @keyframes pulseActive {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.15); opacity: 0.8; }
    }
    .node-endpoint {
      transform-origin: center;
      transform-box: fill-box;
    }

    /* The loop has different paths animated at different phases */
    .path-1 { animation-delay: 0s; }
    .path-2 { animation-delay: 1.5s; }
    .path-3 { animation-delay: 3s; }
    .path-4 { animation-delay: 4.5s; }

    /* Path nodes pulse with their path */
    .endpoint-1 { animation: pulseActive 6s ease-in-out 1s infinite; }
    .endpoint-2 { animation: pulseActive 6s ease-in-out 2.5s infinite; }
    .endpoint-3 { animation: pulseActive 6s ease-in-out 4s infinite; }
    .endpoint-4 { animation: pulseActive 6s ease-in-out 5.5s infinite; }

    /* Reduced motion */
    @media (prefers-reduced-motion: reduce) {
      .path-active, .endpoint-1, .endpoint-2, .endpoint-3, .endpoint-4 {
        animation: none !important;
        stroke-dashoffset: 0;
      }
    }
  </style>

  <!-- Scene 0 (start) - centered top -->
  <g transform="translate(300, 40)">
    <circle class="node node-start node-circle" />
    <text class="label" y="22">scene 1</text>
  </g>

  <!-- 3 branches going to scenes 2, 3, 4 (middle row) -->
  <path class="path path-active path-1" d="M 300,55 Q 200,90 100,140" />
  <path class="path path-active path-2" d="M 300,55 L 300,140" />
  <path class="path path-active path-3" d="M 300,55 Q 400,90 500,140" />

  <!-- Scene 2 (left), Scene 3 (middle), Scene 4 (right) -->
  <g class="endpoint-1" transform="translate(100, 150)">
    <circle class="node node-endpoint node-circle" r="6" />
    <text class="label" y="22">scene 2</text>
  </g>
  <g class="endpoint-2" transform="translate(300, 150)">
    <circle class="node node-endpoint node-circle" r="6" />
    <text class="label" y="22">scene 3</text>
  </g>
  <g class="endpoint-3" transform="translate(500, 150)">
    <circle class="node node-endpoint node-circle" r="6" />
    <text class="label" y="22">scene 4</text>
  </g>

  <!-- 5 sub-paths from these scenes to 5 different endings -->
  <path class="path path-active path-1" d="M 100,165 Q 60,210 50,260" />
  <path class="path path-active path-2" d="M 100,165 Q 200,210 200,260" />
  <path class="path path-active path-3" d="M 300,165 L 300,260" />
  <path class="path path-active path-4" d="M 500,165 Q 400,210 400,260" />
  <path class="path path-active path-2" d="M 500,165 Q 540,210 550,260" />

  <!-- 5 endpoint circles at the bottom -->
  <g class="endpoint-1" transform="translate(50, 270)">
    <circle class="node node-endpoint node-circle" r="4" />
  </g>
  <g class="endpoint-2" transform="translate(200, 270)">
    <circle class="node node-endpoint node-circle" r="4" />
  </g>
  <g class="endpoint-3" transform="translate(300, 270)">
    <circle class="node node-endpoint node-circle" r="4" />
  </g>
  <g class="endpoint-4" transform="translate(400, 270)">
    <circle class="node node-endpoint node-circle" r="4" />
  </g>
  <g class="endpoint-2" transform="translate(550, 270)">
    <circle class="node node-endpoint node-circle" r="4" />
  </g>

  <!-- Statistic label below -->
  <text class="label-eyebrow" x="300" y="305">multiple endings · one story · your choices</text>
</svg>'''
