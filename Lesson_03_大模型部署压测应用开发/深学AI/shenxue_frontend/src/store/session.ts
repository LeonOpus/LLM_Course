import { proxy } from 'valtio'

const state = proxy({
  list: [] as API.Session[],
})

const actions = {
  setList(list: API.Session[]) {
    state.list = list
  },
  add(item: API.Session) {
    state.list.push(item)
  },
}

export const sessionState = state
export const sessionActions = actions
