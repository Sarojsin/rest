// Polyfill Request/Response for MSW in Node.js environment
import 'whatwg-fetch';

// Polyfill TextEncoder/TextDecoder for MSW
import { TextEncoder, TextDecoder } from 'util';
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Polyfill TransformStream, WritableStream, ReadableStream for MSW
import { TransformStream, WritableStream, ReadableStream } from 'stream/web';
global.TransformStream = TransformStream;
global.WritableStream = WritableStream;
global.ReadableStream = ReadableStream;

// Polyfill BroadcastChannel for MSW
global.BroadcastChannel = class BroadcastChannel {
  constructor(name) {
    this.name = name;
  }
  name;
  postMessage(message) {}
  close() {}
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() { return true; }
  onmessage = null;
  onmessageerror = null;
};

// Polyfill Headers.getSetCookie for MSW
if (typeof global.Headers !== 'undefined' && !global.Headers.prototype.getSetCookie) {
  global.Headers.prototype.getSetCookie = function() {
    const setCookieHeader = this.get('set-cookie');
    if (!setCookieHeader) return [];
    return Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
  };
}

jest.mock('expo-local-authentication', () => ({
  hasHardwareAsync: jest.fn().mockResolvedValue(true),
  isEnrolledAsync: jest.fn().mockResolvedValue(true),
  supportedAuthenticationTypesAsync: jest.fn().mockResolvedValue([1]),
  authenticateAsync: jest.fn().mockResolvedValue({ success: true }),
  AuthenticationType: {
    FACIAL_RECOGNITION: 1,
    FINGERPRINT: 2,
    IRIS: 3,
  },
}));

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn().mockResolvedValue(null),
  setItemAsync: jest.fn().mockResolvedValue(undefined),
  deleteItemAsync: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('expo-constants', () => ({
  expoConfig: {
    extra: {
      apiBaseUrl: 'http://localhost:8000',
    },
  },
}));

jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Ionicons',
}));

jest.mock('react-native/Libraries/Animated/NativeAnimatedHelper', () => {}, { virtual: true });

jest.mock('react-native', () => ({
  View: 'View',
  Text: 'Text',
  TouchableOpacity: 'TouchableOpacity',
  ScrollView: 'ScrollView',
  FlatList: 'FlatList',
  StyleSheet: { create: (x) => x },
  Platform: { OS: 'ios', select: (obj) => obj.ios || obj.default },
  NativeModules: {},
  requireNativeComponent: () => 'NativeComponent',
  findNodeHandle: () => null,
  useWindowDimensions: () => ({ width: 375, height: 812 }),
  AccessibilityInfo: { announceForAccessibility: jest.fn() },
  AppState: { addEventListener: jest.fn(), removeEventListener: jest.fn(), currentState: 'active' },
  Alert: { alert: jest.fn() },
  Dimensions: { get: () => ({ width: 375, height: 812 }) },
  PixelRatio: { get: () => 2 },
  Image: 'Image',
  Keyboard: { dismiss: jest.fn() },
  Linking: { openURL: jest.fn() },
  PermissionsAndroid: { request: jest.fn().mockResolvedValue('granted') },
  ToastAndroid: { show: jest.fn() },
  Vibration: { vibrate: jest.fn() },
  StatusBar: 'StatusBar',
  SafeAreaView: 'SafeAreaView',
  ActivityIndicator: 'ActivityIndicator',
  Modal: 'Modal',
  Pressable: 'Pressable',
  RefreshControl: 'RefreshControl',
  SectionList: 'SectionList',
  VirtualizedList: 'VirtualizedList',
}, { virtual: true }));

global.__DEV__ = true;

const mockSafeAreaContext = {
  SafeAreaProvider: ({ children }) => children,
  SafeAreaView: ({ children, ...props }) => {
    const React = require('react');
    return React.createElement('div', props, children);
  },
};

jest.mock('react-native-safe-area-context', () => mockSafeAreaContext);

jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  Reanimated.default.call = () => {};
  return Reanimated;
});

jest.mock('expo-router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
  }),
  useLocalSearchParams: () => ({}),
  Link: ({ children, ...props }) => {
    const React = require('react');
    return React.createElement('a', props, children);
  },
  Stack: {
    Screen: ({ children }) => children,
  },
}));

// Note: @tanstack/react-query is NOT mocked here - tests use real QueryClient and QueryClientProvider

jest.mock('@/lib/auth', () => ({
  useAuth: () => ({
    me: { id: 'user-1', email: 'test@example.com', display_name: 'Test User' },
    getRestaurantId: () => 'restaurant-1',
    getBranchId: () => 'branch-1',
    memberships: [{ id: 'membership-1', restaurant_id: 'restaurant-1', role: 'OWNER', permissions: ['*'] }],
    active_branch_id: 'branch-1',
  }),
}));

// Mock config to use empty base URL for MSW interception
jest.mock('@/lib/config', () => ({
  API_BASE_URL: '',
  IS_DEV: true,
}));

// Mock tokenStore to avoid Platform.OS issues
jest.mock('@/lib/tokenStore', () => ({
  getAccessToken: jest.fn().mockResolvedValue('mock-access-token'),
  getRefreshToken: jest.fn().mockResolvedValue('mock-refresh-token'),
  setTokens: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('@/theme/context', () => ({
  useTheme: () => ({
    color: { ink: '#000', muted: '#666', primary: '#007AFF', background: '#FFF' },
  }),
}));