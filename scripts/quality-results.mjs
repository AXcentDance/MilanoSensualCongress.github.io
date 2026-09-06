export const categories = ['performance', 'accessibility', 'best-practices', 'seo'];

export function belowTarget(result) {
  return !!result.runtimeError || categories.some(category =>
    (category !== 'seo' || result.indexable) &&
    (!Number.isFinite(result.scores[category]) || result.scores[category] < 95));
}

export function aggregateResults(results) {
  const groups = new Map();
  for (const result of results) {
    const key = result.file + ':' + result.profile;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(result);
  }
  return [...groups.values()].map(group => {
    const scores = {}, ranges = {};
    for (const category of categories) {
      const values = group.map(r => r.scores[category]).sort((a,b) => a-b);
      const valid = values.every(Number.isFinite);
      const middle = Math.floor(values.length / 2);
      const median = values.length % 2 ? values[middle] : (values[middle-1]+values[middle])/2;
      // Timing varies; intermittent accessibility or integration failures still matter.
      scores[category] = valid ? (category === 'performance' ? median : values[0]) : null;
      ranges[category] = valid ? [values[0], values.at(-1)] : null;
    }
    return { file: group[0].file, path: group[0].path, indexable: group[0].indexable,
      profile: group[0].profile, runs: group.length, scores, ranges,
      runtimeError: group.some(r => r.runtimeError), reports: group.map(r => r.report) };
  });
}
