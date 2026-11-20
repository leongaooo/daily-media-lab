/** The DOM is the authority for line wrapping after the declared font is ready. */
export const captionTextStyle = {
  whiteSpace: "pre-line",
  overflowWrap: "anywhere",
  flex: "1 1 auto",
  minWidth: "0",
} as const;

export const captionRailStyle = {
  position: "absolute",
  left: "0",
  right: "0",
  top: "904px",
  height: "176px",
  boxSizing: "border-box",
  padding: "22px 80px",
  display: "flex",
  alignItems: "center",
  background: "#050C14",
  borderTop: "1px solid #46515E",
  color: "#F8FBFA",
  fontSize: "36px",
  lineHeight: "1.35",
} as const;

export type CaptionMeasurement = {
  cue_index: number;
  content_height: number;
  available_height: number;
  content_width: number;
  available_width: number;
};

/** Fail before capture, never resize the font or invent timings for frozen speech. */
export const verifyCaptionLayout = (
  cues: { text: string }[],
  fontFamily = '"EditorialProjectFont", sans-serif',
): CaptionMeasurement[] => {
  const rail = document.createElement("div");
  Object.assign(rail.style, captionRailStyle, {
    position: "fixed",
    top: "0",
    left: "-10000px",
    right: "auto",
    width: "1920px",
    visibility: "hidden",
    fontFamily,
  });
  const text = document.createElement("div");
  Object.assign(text.style, captionTextStyle);
  rail.appendChild(text);
  document.body.appendChild(rail);
  try {
    const railCss = getComputedStyle(rail);
    const availableHeight =
      rail.clientHeight -
      parseFloat(railCss.paddingTop) -
      parseFloat(railCss.paddingBottom);
    const availableWidth =
      rail.clientWidth -
      parseFloat(railCss.paddingLeft) -
      parseFloat(railCss.paddingRight);
    return cues.map((cue, index) => {
      text.textContent = cue.text;
      const height = text.scrollHeight;
      const width = text.scrollWidth;
      if (height > availableHeight + 1 || width > availableWidth + 1) {
        throw new Error(
          `Caption cue ${index + 1} exceeds the fixed y904-1080 rail (${width}x${height}, available ${availableWidth}x${availableHeight}). Split the cue at measured semantic audio boundaries; frozen narration was not modified.`,
        );
      }
      return {
        cue_index: index,
        content_height: height,
        available_height: availableHeight,
        content_width: width,
        available_width: availableWidth,
      };
    });
  } finally {
    rail.remove();
  }
};
