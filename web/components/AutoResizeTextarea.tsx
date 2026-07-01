"use client";

import { TextareaHTMLAttributes, useEffect, useRef } from "react";

type AutoResizeTextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

function resizeTextarea(textarea: HTMLTextAreaElement) {
  textarea.style.height = "auto";
  textarea.style.height = `${textarea.scrollHeight}px`;
}

export default function AutoResizeTextarea({
  value,
  onChange,
  className,
  rows = 1,
  ...props
}: AutoResizeTextareaProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (ref.current) {
      resizeTextarea(ref.current);
    }
  }, [value]);

  return (
    <textarea
      ref={ref}
      rows={rows}
      value={value}
      onChange={(event) => {
        onChange?.(event);
        resizeTextarea(event.currentTarget);
      }}
      className={className}
      {...props}
    />
  );
}
