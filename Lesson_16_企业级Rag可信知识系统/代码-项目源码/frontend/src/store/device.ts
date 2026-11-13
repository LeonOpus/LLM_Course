import { proxy } from 'valtio'

const state = proxy({
  chatting: false,
})

const actions = {
  setChatting(chatting: boolean) {
    state.chatting = chatting
  },
}

export const deviceState = state
export const deviceActions = actions
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* revision: lpf2-18Lb8 lpf2-19A32 */
