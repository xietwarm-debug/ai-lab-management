const DEVICE_KEY = "local_device_profile_v1";

function buildFallbackDeviceId() {
  return `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function ensureLocalDeviceProfile() {
  let profile = uni.getStorageSync(DEVICE_KEY);
  if (profile && typeof profile === "object" && profile.deviceId) {
    return profile;
  }
  const systemInfo = uni.getSystemInfoSync ? uni.getSystemInfoSync() : {};
  const platform = String((systemInfo && systemInfo.platform) || "").trim() || "unknown";
  const model = String((systemInfo && systemInfo.model) || "").trim() || "unknown-device";
  profile = {
    deviceId: buildFallbackDeviceId(),
    deviceName: `${platform}-${model}`.slice(0, 120),
    platform
  };
  uni.setStorageSync(DEVICE_KEY, profile);
  return profile;
}
