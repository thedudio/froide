function scrollToAnchor(id: string) {
  window.setTimeout(() => {
    const el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.scrollIntoView(true);
  }, 100);
}

const getHeight = (el: HTMLElement) => {
  const style = window.getComputedStyle(el);
  const display = style.display;
  const position = style.position;
  const visibility = style.visibility;
  const maxHeight = style.maxHeight && style.maxHeight.replace("px", "").replace("%", "");
  let wantedHeight = 0;

  // if its not hidden we just return normal height
  if (display !== "none" && maxHeight !== "0") {
    return el.offsetHeight;
  }

  // the element is hidden so:
  // making the el block so we can meassure its height but still be hidden
  el.style.position = "absolute";
  el.style.visibility = "hidden";
  el.style.display = "block";

  wantedHeight = el.offsetHeight;

  // reverting to the original values
  el.style.display = display;
  el.style.position = position;
  el.style.visibility = visibility;

  return wantedHeight;
};

 /**
  * toggleSlide mimics the jQuery version of slideDown and slideUp
  * all in one function comparing the max-heigth to 0
  */
const toggleSlide = (el: HTMLElement, seconds = 2) => {
  let elMaxHeight = "0px";

  if (el.getAttribute("data-max-height")) {
    // we've already used this before, so everything is setup
    let maxHeight = el.style.maxHeight;
    maxHeight = maxHeight && maxHeight.replace("px", "").replace("%", "");
    if (maxHeight === "0") {
      el.style.maxHeight = el.getAttribute("data-max-height") || "0";
    } else {
      el.style.maxHeight = "0";
    }
  } else {
    elMaxHeight = getHeight(el) + "px";
    el.style.transition = `max-height ${seconds}s ease-in-out`;
    el.style.overflow = "hidden";
    el.style.maxHeight = "0";
    el.setAttribute("data-max-height", elMaxHeight);
    el.style.display = "block";

    // we use setTimeout to modify maxHeight later than display (so we have the transition effect)
    setTimeout(() => {
      el.style.maxHeight = elMaxHeight;
    }, 10);
  }
};

export {
  scrollToAnchor,
  toggleSlide,
};
