import storage from './storage'
import proxyWithPersist, { PersistStrategy } from './valtio-persist'

const state = proxyWithPersist({
  name: 'user',
  version: 0,
  getStorage: () => storage,
  persistStrategies: {
    token: PersistStrategy.SingleFile,
    username: PersistStrategy.SingleFile,
  },
  migrations: {},

  initialState: {
    token: null as string | null,
    username: null as string | null,
  },
})

const actions = {
  setToken(token: string) {
    state.token = token
  },
  setUsername(username: string) {
    state.username = username
  },
}

export const userState = state
export const userActions = actions
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
// checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
// checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
// checksum: lpf2-18Lb8 lpf2-19A32
