# Imagery

Rendered with Codex CLI image generation (`codex exec --enable image_generation`) as PNGs with alpha, so they sit directly on whatever the canvas token is. Every subject is ROSARIO's: the rosary, the rotary dial with a rose, the telephone.

| File | Slot | Subject |
|---|---|---|
| rosary.png | hero, right column | a complete rosary loop of red glass beads with a rotary-dial medallion in place of a cross, whole object with margin, 2:3 |
| dial.png | scoring plate (circle) | a rotary telephone dial as one red glass object, ten holes, a glass rose bud at the center, 1:1 |
| handset.png | closing CTA band | a complete red glass handset with coiled cord, whole object with margin, 1:1 |

Glass colors only: #5e1f25, #bc0400, #fe0600 with ember highlights. No text, logos or people. Ask for "transparent background (alpha), no backdrop, no ground shadow" and "one complete object fully inside the frame with margin, nothing cropped" every time; the page shows these with object-fit: contain and never crops or scales them.

The pages load the `.webp` copies (quality 88, made from the PNGs with Pillow). The PNGs are the source assets; regenerate the WebP files from them after any change.
