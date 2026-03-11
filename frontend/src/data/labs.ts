export type LabItem = { lab_name: string; fluid: string; category: string };

export const LAB_CATEGORIES: Record<string, LabItem[]> = {};

export const ALL_LABS: LabItem[] = Object.values(LAB_CATEGORIES).flat();
