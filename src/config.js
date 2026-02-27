import fs from 'node:fs';
import path from 'node:path';

export function loadConfig() {
  const configPath = process.env.INCENTIVOS_CONFIG || 'config/incentivos_config.json';
  const abs = path.isAbsolute(configPath) ? configPath : path.join(process.cwd(), configPath);
  if (!fs.existsSync(abs)) {
    throw new Error(
      `No existe ${abs}. Copia config/incentivos_config.example.json a ${abs} y ajusta si corresponde.`
    );
  }
  const raw = fs.readFileSync(abs, 'utf-8');
  return JSON.parse(raw);
}
