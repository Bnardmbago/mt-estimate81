"use client";

import { createElement, Fragment, type ReactElement } from "react";
import {
  accentDefinitions,
  accentLineBorderUnderlay,
  accentShapeSvgProps,
  accentShapeTransform,
  type AccentDefinition,
  type AccentPageDimensions,
  type AccentShape,
  type AccentSvgProps,
} from "@/lib/cover-accent-shapes";

type Props = {
  shape: AccentShape;
  themeAccent: string;
  page: AccentPageDimensions;
};

const PRIMITIVE_TAG: Record<AccentShape["type"], string> = {
  rectangle: "rect",
  line: "line",
  circle: "circle",
  ellipse: "ellipse",
  triangle: "polygon",
  polygon: "polygon",
};

/**
 * Render a single validated accent shape plus its generated definitions. The
 * group is rotated about the page-mm bounding-box center so the underlay and
 * primitive rotate together, matching the backend PDF renderer.
 */
export default function PresentationAccentShapeSvg({ shape, themeAccent, page }: Props) {
  const definitions = accentDefinitions([shape], themeAccent);
  const props = accentShapeSvgProps(shape, themeAccent, page);
  const transform = accentShapeTransform(shape, page);
  const underlay = accentLineBorderUnderlay(shape, page);

  return (
    <g data-accent-id={shape.id} transform={transform}>
      {definitions.length > 0 ? (
        <defs>{definitions.map(renderDefinition)}</defs>
      ) : null}
      {underlay ? <line {...(underlay as Record<string, string | number>)} /> : null}
      {createElement(PRIMITIVE_TAG[shape.type], props)}
    </g>
  );
}

function renderDefinition(definition: AccentDefinition): ReactElement {
  if (definition.kind === "linearGradient") {
    return (
      <linearGradient key={definition.id} id={definition.id} {...svgAttrs(definition.props)}>
        {(definition.stops ?? []).map((stop, index) => (
          <stop key={index} offset={stop.offset} stopColor={stop.color} />
        ))}
      </linearGradient>
    );
  }
  if (definition.kind === "radialGradient") {
    return (
      <radialGradient key={definition.id} id={definition.id} {...svgAttrs(definition.props)}>
        {(definition.stops ?? []).map((stop, index) => (
          <stop key={index} offset={stop.offset} stopColor={stop.color} />
        ))}
      </radialGradient>
    );
  }
  return (
    <pattern key={definition.id} id={definition.id} {...svgAttrs(definition.props)}>
      {renderPatternContent(definition)}
    </pattern>
  );
}

function renderPatternContent(definition: AccentDefinition): ReactElement {
  const decoration = definition.decoration ?? {
    color: "#ffffff",
    scale: 1,
    spacing: 1,
    opacity: 0.25,
  };
  const tile = decoration.scale * decoration.spacing;
  const stroke = Math.max(0.1, decoration.scale * 0.25);
  const background = (
    <rect
      width={definition.props.width}
      height={definition.props.height}
      fill={definition.backgroundFill}
    />
  );

  if (definition.patternType === "dots") {
    return (
      <Fragment>
        {background}
        <circle
          cx={tile / 2}
          cy={tile / 2}
          r={Math.max(0.1, decoration.scale * 0.35)}
          fill={decoration.color}
          opacity={decoration.opacity}
        />
      </Fragment>
    );
  }

  const path =
    definition.patternType === "grid"
      ? `M 0 0 H ${tile} M 0 0 V ${tile}`
      : definition.patternType === "diagonal_hatch"
        ? `M 0 ${tile} L ${tile} 0 M ${-tile} ${tile} L 0 0 M ${tile} ${tile} L ${tile * 2} 0`
        : `M 0 0 V ${tile} M ${tile / 2} 0 V ${tile}`;

  return (
    <Fragment>
      {background}
      <path
        d={path}
        stroke={decoration.color}
        strokeWidth={stroke}
        opacity={decoration.opacity}
        fill="none"
      />
    </Fragment>
  );
}

function svgAttrs(props: AccentSvgProps): Record<string, string | number> {
  return props as Record<string, string | number>;
}
