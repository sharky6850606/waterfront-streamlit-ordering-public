export function getTodayDateValue(now = new Date()) {
  const year = now.getFullYear();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function getDateRangeFromValue(value?: string | null) {
  const safeValue = /^\d{4}-\d{2}-\d{2}$/.test(value ?? "")
    ? (value as string)
    : getTodayDateValue();

  const [year, month, day] = safeValue.split("-").map(Number);
  const start = new Date(year, month - 1, day);
  const end = new Date(year, month - 1, day + 1);

  return {
    value: safeValue,
    start,
    end
  };
}
