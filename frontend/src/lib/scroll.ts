/**
 * Scroll only the nearest scrollable box so `el` comes into view.
 * Unlike `scrollIntoView`, this never moves outer boxes or the page itself,
 * which used to push the whole app up and leave an empty band below it.
 */
export function scrollWithin(el: HTMLElement | null, block: "start" | "end" = "start", behavior: ScrollBehavior = "smooth") {
  if (!el) return;
  let box = el.parentElement;
  while (box && !/(auto|scroll)/.test(getComputedStyle(box).overflowY)) box = box.parentElement;
  if (!box) return;
  const boxRect = box.getBoundingClientRect();
  const rect = el.getBoundingClientRect();
  const offset = block === "start" ? rect.top - boxRect.top : rect.bottom - boxRect.bottom;
  box.scrollTo({ top: box.scrollTop + offset, behavior });
}
