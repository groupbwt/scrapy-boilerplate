export async function pauseFor(timeout) {
  return new Promise((resolve, reject) => {
    try {
      setTimeout(() => {
        resolve();
      }, timeout);
    } catch (e) {
      reject(new Error(e.toString()));
    }
  });
}
