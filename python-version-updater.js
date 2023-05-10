module.exports = {
  readVersion(contents) {
    const versionPattern = /__version__\s*=\s*'(\d+\.\d+\.\d+)'/;
    const match = contents.match(versionPattern);

    if (match && match[1]) {
      return match[1];
    }

    throw new Error('Version not found');
  },

  writeVersion(contents, version) {
    const versionPattern = /(__version__\s*=\s*')(\d+\.\d+\.\d+)(')/;
    const newContents = contents.replace(versionPattern, `$1${version}$3`);

    if (newContents === contents) {
      throw new Error('Version not updated');
    }

    return newContents;
  },
};
