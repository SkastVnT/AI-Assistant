export function convertToMultipleOfNFloor(num, n) {
  let clamped = Math.max(-128, Math.min(128, num));
  let floored = Math.floor(clamped / n) * n;
  return Math.max(-128, Math.min(128, floored));
}

export function checkNumberInRange(num, min, max, def, returnInt=false) {
    let ret = num;

    if (num > max || num < min) {
        return def;
    }

    if (returnInt)
        ret = Math.floor(num);

    return ret;
}

