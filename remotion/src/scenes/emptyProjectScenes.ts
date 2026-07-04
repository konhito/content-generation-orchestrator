import React from "react";

export type SceneComponent = React.FC<Record<string, unknown>>;

export const PROJECT_SCENES: Record<string, SceneComponent> = {};
