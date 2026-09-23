import { ColormapTheme } from '../types/signal';

// Fast RGB colormap interpolators for RF waterfall / spectrogram heatmap rendering
export function getColormapColor(val: number, theme: ColormapTheme): [number, number, number] {
  // val is normalized 0.0 to 1.0
  const t = Math.max(0, Math.min(1, val));

  switch (theme) {
    case 'turbo':
      return interpolateTurbo(t);
    case 'viridis':
      return interpolateViridis(t);
    case 'inferno':
      return interpolateInferno(t);
    case 'plasma':
      return interpolatePlasma(t);
    case 'matrix':
      return [
        Math.floor(t * 30),
        Math.floor(t * 255),
        Math.floor(t * 70),
      ];
    case 'cyan':
    default:
      return [
        Math.floor(t * 10),
        Math.floor(t * 240),
        Math.floor(200 + t * 55),
      ];
  }
}

function interpolateViridis(t: number): [number, number, number] {
  const c0 = [68, 1, 84];
  const c1 = [59, 82, 139];
  const c2 = [33, 145, 140];
  const c3 = [94, 201, 98];
  const c4 = [253, 231, 37];

  if (t < 0.25) return mixColors(c0, c1, t / 0.25);
  if (t < 0.5) return mixColors(c1, c2, (t - 0.25) / 0.25);
  if (t < 0.75) return mixColors(c2, c3, (t - 0.5) / 0.25);
  return mixColors(c3, c4, (t - 0.75) / 0.25);
}

function interpolateInferno(t: number): [number, number, number] {
  const c0 = [0, 0, 4];
  const c1 = [87, 16, 110];
  const c2 = [187, 55, 84];
  const c3 = [249, 142, 9];
  const c4 = [252, 255, 164];

  if (t < 0.25) return mixColors(c0, c1, t / 0.25);
  if (t < 0.5) return mixColors(c1, c2, (t - 0.25) / 0.25);
  if (t < 0.75) return mixColors(c2, c3, (t - 0.5) / 0.25);
  return mixColors(c3, c4, (t - 0.75) / 0.25);
}

function interpolatePlasma(t: number): [number, number, number] {
  const c0 = [13, 8, 135];
  const c1 = [126, 3, 168];
  const c2 = [204, 71, 120];
  const c3 = [248, 149, 64];
  const c4 = [240, 249, 33];

  if (t < 0.25) return mixColors(c0, c1, t / 0.25);
  if (t < 0.5) return mixColors(c1, c2, (t - 0.25) / 0.25);
  if (t < 0.75) return mixColors(c2, c3, (t - 0.5) / 0.25);
  return mixColors(c3, c4, (t - 0.75) / 0.25);
}

function interpolateTurbo(t: number): [number, number, number] {
  const c0 = [48, 18, 59];
  const c1 = [70, 134, 251];
  const c2 = [27, 229, 181];
  const c3 = [164, 252, 60];
  const c4 = [251, 185, 56];
  const c5 = [227, 68, 34];

  if (t < 0.2) return mixColors(c0, c1, t / 0.2);
  if (t < 0.4) return mixColors(c1, c2, (t - 0.2) / 0.2);
  if (t < 0.6) return mixColors(c2, c3, (t - 0.4) / 0.2);
  if (t < 0.8) return mixColors(c3, c4, (t - 0.6) / 0.2);
  return mixColors(c4, c5, (t - 0.8) / 0.2);
}

function mixColors(c1: number[], c2: number[], factor: number): [number, number, number] {
  const f = Math.max(0, Math.min(1, factor));
  return [
    Math.round(c1[0] + (c2[0] - c1[0]) * f),
    Math.round(c1[1] + (c2[1] - c1[1]) * f),
    Math.round(c1[2] + (c2[2] - c1[2]) * f),
  ];
}
