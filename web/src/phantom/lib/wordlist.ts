/** Pre-vetted lab dictionary — common weak PSK material used for authorized verification. */
export const APPROVED_DICTIONARY: string[] = [
  "Welcome1",
  "sensornet",
  "ChangeMe!",
  "password",
  "admin1234",
  "12345678",
  "marriott1",
  "ring12345",
  "password1",
  "password123",
  "Password1",
  "Password123",
  "123456789",
  "1234567890",
  "qwerty123",
  "qwertyui",
  "admin123",
  "administrator",
  "letmein1",
  "welcome1",
  "welcome123",
  "Welcome123",
  "guest123",
  "guestguest",
  "changeme",
  "ChangeMe",
  "changeme1",
  "Summer2024",
  "Summer2024!",
  "Summer2025",
  "Winter2024",
  "Spring2024",
  "Fall2024!",
  "Hopper2024",
  "hopper123",
  "corpguest",
  "CorpGuest1",
  "SensorNet1",
  "iotadmin1",
  "marriott",
  "Marriott1",
  "hotelguest",
  "ringdoorbell",
  "tesla1234",
  "printer1",
  "printscan",
  "wifi1234",
  "wireless",
  "internet",
  "linksys1",
  "netgear1",
  "NETGEAR1",
  "tplink12",
  "default1",
  "passw0rd",
  "P@ssw0rd",
  "P@ssword1",
  "Abc12345",
  "abcd1234",
  "asdfasdf",
  "iloveyou",
  "monkey12",
  "dragon12",
  "baseball",
  "football",
  "starwars",
  "superman",
  "batman12",
  "trustno1",
  "ncc1701a",
  "hunter2!",
  "letmein!",
  "secret12",
  "shadow12",
  "master12",
  "access12",
  "login123",
  "pass1234",
  "pass12345",
  "company1",
  "corporate",
  "office12",
  "nashville",
  "Nashville1",
  "tennessee",
  "musiccity",
  "broadway1",
  "civicwifi",
  "freewifi1",
  "openwifi1",
  "guestwifi",
  "voipadmin",
  "voice1234",
  "camera12",
  "security1",
  "monitor1",
  "defaultpsk",
  "factory1",
  "setup123",
  "install1",
  "TempPass1",
  "Temporary",
  "changeme!",
  "ChangeMe1",
  "Welcome!",
  "Welcome12",
  "GuestAccess",
  "GuestWifi1",
  "IoTNetwork",
  "smartHome",
  "smarthome",
  "homewifi1",
  "familywifi",
  "mywireless",
  "thisisunsafe",
  "correcthorsebatterystaple",
];

export function expandRules(word: string): string[] {
  const out = new Set<string>();
  const push = (w: string) => {
    if (w.length >= 8 && w.length <= 63) out.add(w);
  };
  push(word);
  const cap = word.charAt(0).toUpperCase() + word.slice(1);
  push(cap);
  for (const s of ["1", "!", "123", "2024", "2025", "2026", "1!"]) push(word + s);
  for (const s of ["1", "!", "123", "2024"]) push(cap + s);
  if (word === word.toLowerCase()) push(word.toUpperCase());
  return [...out];
}

export function buildAttackList(base: string[] = APPROVED_DICTIONARY): string[] {
  const seen = new Set<string>();
  const list: string[] = [];
  for (const w of base) {
    for (const e of expandRules(w)) {
      if (!seen.has(e)) {
        seen.add(e);
        list.push(e);
      }
    }
  }
  return list;
}
