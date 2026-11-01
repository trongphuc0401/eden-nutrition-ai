// One place for every content image. To use a real photo, drop it in public/images/
// (e.g. report-cover.jpg), then change `src` here. Keep the same aspect ratio.
export const images = {
  reportCover: { src: "/images/report-cover.svg", alt: "Ly sinh tố cam bên lát cam và ổi", width: 1200, height: 500 },
  emptyHistory: { src: "/images/empty-history.svg", alt: "", width: 480, height: 320 },
  emptySaved: { src: "/images/empty-saved.svg", alt: "", width: 480, height: 320 },
  processing: { src: "/images/processing.svg", alt: "", width: 480, height: 320 },
} as const;

export type ImageKey = keyof typeof images;
