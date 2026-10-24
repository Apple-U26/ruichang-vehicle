import assert from 'node:assert/strict'
import { afterEach, beforeEach, test } from 'node:test'
import { getRememberedDriverName, normalizeDriverName, rememberDriverName } from '../src/utils/driverName.js'

const originalStorage = globalThis.localStorage
let values
beforeEach(() => {
  values = new Map()
  globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  }
})
afterEach(() => {
  if (originalStorage === undefined) delete globalThis.localStorage
  else globalThis.localStorage = originalStorage
})

test('first use never inherits registration name or legacy shared memory', () => {
  values.set('lastDriverName', '旧账号驾驶员')
  assert.equal(getRememberedDriverName({ id: 1, real_name: '注册账号名称' }), '')
})

test('remembers exact actual name per account and trims only outer spaces', () => {
  const first = { id: 1, real_name: '注册账号名称' }
  const second = { id: 2, real_name: '另一账号' }
  rememberDriverName(first, '  张 三  ')
  assert.equal(getRememberedDriverName(first), '张 三')
  assert.equal(getRememberedDriverName(second), '')
  rememberDriverName(second, '李四')
  assert.equal(getRememberedDriverName(first), '张 三')
  assert.equal(getRememberedDriverName(second), '李四')
  rememberDriverName(first, '王五')
  assert.equal(getRememberedDriverName(first), '王五')
})

test('blank or malformed names do not overwrite the last valid name', () => {
  const user = { id: 1 }
  rememberDriverName(user, '张三')
  for (const value of ['  ', null, undefined, 123, '名'.repeat(51)]) rememberDriverName(user, value)
  assert.equal(getRememberedDriverName(user), '张三')
  assert.equal(normalizeDriverName('   '), '')
})

test('username fallback cannot collide with numeric account ids', () => {
  rememberDriverName({ id: 1 }, '甲')
  rememberDriverName({ username: '1' }, '乙')
  rememberDriverName({}, '丙')
  assert.equal(getRememberedDriverName({ id: 1 }), '甲')
  assert.equal(getRememberedDriverName({ username: '1' }), '乙')
  assert.equal(getRememberedDriverName({}), '')
})

test('unavailable browser storage cannot fail a successful registration', () => {
  globalThis.localStorage = {
    getItem() { throw new Error('Storage disabled') },
    setItem() { throw new Error('Storage full') },
  }
  assert.equal(getRememberedDriverName({ id: 1 }), '')
  assert.doesNotThrow(() => rememberDriverName({ id: 1 }, '张三'))
})
