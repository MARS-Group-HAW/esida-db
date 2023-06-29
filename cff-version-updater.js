module.exports = {
  readVersion(contents) {
    const versionPattern = /version:\s*(\d+\.\d+\.\d+)/;
    const match = contents.match(versionPattern);

    if (match && match[1]) {
      return match[1];
    }

    throw new Error('CFF Version not found');
  },

  writeVersion(contents, version) {
    const versionPattern = /^(version:\s*)(\d+\.\d+\.\d+)/gm;
    const newContents = contents.replace(versionPattern, `$1${version}`);

    if (newContents === contents) {
      throw new Error('CFF Version not updated');
    }

    const datePattern = /(date-released:\s*')(\d+-\d+-\d+)(')/;

    var todayDate = new Date();
    var date = todayDate.toISOString().substring(0, 10);

    const newnewContents = newContents.replace(datePattern, `$1${date}$3`);

    if (newnewContents === newContents) {
      throw new Error('CFF Date not updated');
    }

    return newnewContents;
  },
};
