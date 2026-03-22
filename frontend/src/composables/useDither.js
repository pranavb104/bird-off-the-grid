/**
 * Bayer 4×4 dither engine for canvas-based pixel shadows and fills.
 * Extracted from the dithered-ui.html reference.
 */

const BAYER4 = [
  [ 0/16,  8/16,  2/16, 10/16],
  [12/16,  4/16, 14/16,  6/16],
  [ 3/16, 11/16,  1/16,  9/16],
  [15/16,  7/16, 13/16,  5/16],
]

const INK_R = 10, INK_G = 10, INK_B = 10

/**
 * Render a gradient-density dithered shadow onto a canvas.
 * The shadow fades from sparse (top-left) to dense (bottom-right).
 */
export function renderDitherShadow(canvas, intensity = 0.55, explicitW, explicitH) {
  const W = explicitW || canvas.parentElement.offsetWidth
  const H = explicitH || canvas.parentElement.offsetHeight
  if (W === 0 || H === 0) return

  canvas.width  = W
  canvas.height = H
  canvas.style.width  = W + 'px'
  canvas.style.height = H + 'px'

  const ctx = canvas.getContext('2d')
  const imageData = ctx.createImageData(W, H)
  const data = imageData.data

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const gradVal = (x / W * 0.5 + y / H * 0.5)
      const density = Math.pow(gradVal, 0.7) * intensity
      const on = density > BAYER4[y % 4][x % 4]
      const idx = (y * W + x) * 4
      data[idx]     = INK_R
      data[idx + 1] = INK_G
      data[idx + 2] = INK_B
      data[idx + 3] = on ? 255 : 0
    }
  }
  ctx.putImageData(imageData, 0, 0)
}

/**
 * Render a solid dithered fill (for dropdown hover states).
 */
export function renderDitherFill(canvas, W, H, intensity = 0.88) {
  canvas.width  = W
  canvas.height = H
  canvas.style.width  = W + 'px'
  canvas.style.height = H + 'px'

  const ctx = canvas.getContext('2d')
  const imageData = ctx.createImageData(W, H)
  const data = imageData.data

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const nudge = (x / W) * 0.15
      const density = Math.min(1, intensity + nudge)
      const on = density > BAYER4[y % 4][x % 4]
      const idx = (y * W + x) * 4
      data[idx]     = INK_R
      data[idx + 1] = INK_G
      data[idx + 2] = INK_B
      data[idx + 3] = on ? 255 : 0
    }
  }
  ctx.putImageData(imageData, 0, 0)
}

/**
 * Find all canvas.dither-drop elements inside a container and render shadows.
 */
export function initDitherShadows(containerEl) {
  if (!containerEl) return
  containerEl.querySelectorAll('canvas.dither-drop').forEach(canvas => {
    const intensity = parseFloat(canvas.dataset.intensity) || 0.55
    renderDitherShadow(canvas, intensity)
  })
}
