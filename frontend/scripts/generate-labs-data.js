const fs = require("fs");
const path = require("path");

const labsPath = path.join(__dirname, "../labs.md");
const outputPath = path.join(__dirname, "../src/lib/labs-data.ts");

const content = fs.readFileSync(labsPath, "utf8");
const lines = content.split("\n").filter(Boolean);
const rows = lines.slice(1); // skip header

function normalizeCategory(s) {
  const t = (s || "").trim();
  if (t === "BLOOD GAS") return "Blood Gas";
  if (t === "CHEMISTRY") return "Chemistry";
  if (t === "category") return null;
  return t || null;
}

const byCat = {};
for (const line of rows) {
  const parts = line.split("\t");
  if (parts.length < 4) continue;
  const [itemid, lab_name, fluid, category] = parts;
  const cat = normalizeCategory(category);
  if (!cat) continue;
  if (!byCat[cat]) byCat[cat] = [];
  byCat[cat].push({
    itemid: itemid.trim(),
    lab_name: lab_name.trim(),
    fluid: fluid.trim(),
  });
}

const allLabs = Object.values(byCat).flat();
const cats = Object.keys(byCat);

const ts = `// Auto-generated from labs.md - run: node scripts/generate-labs-data.js

export interface LabItem {
  itemid: string;
  lab_name: string;
  fluid: string;
}

export type LabCategory = ${cats.map((c) => `"${c}"`).join(" | ")};

export const LABS_BY_CATEGORY: Record<LabCategory, LabItem[]> = ${JSON.stringify(byCat, null, 2)};

export const ALL_LABS: LabItem[] = ${JSON.stringify(allLabs)};
`;

fs.writeFileSync(outputPath, ts);
console.log(
  `Generated ${outputPath}: ${allLabs.length} labs across ${cats.length} categories`
);
