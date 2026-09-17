export function getModelColor(modelName: string): string {
  const lowerName = modelName.toLowerCase();

  if (lowerName.includes("claude")) {
    return "#ff6b35";
  }
  if (lowerName.includes("deepseek")) {
    return "#4d6bfe";
  }
  if (lowerName.includes("qwen")) {
    return "#8b5cf6";
  }

  return "#6b7280";
}
