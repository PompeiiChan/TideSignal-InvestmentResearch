import { chatService } from './chat'
import { configService } from './config'
import { dataSourceService } from './dataSources'
import { layoutService } from './layout'
import { sessionService } from './sessions'
import { traceService } from './traces'

export const investmentService = {
  ...sessionService,
  ...traceService,
  ...dataSourceService,
  ...configService,
  postChatQuery: chatService.postChatQuery,
  postChatQueryStream: chatService.postChatQueryStream,
  postChatRegenerateStream: chatService.postChatRegenerateStream,
  getLayoutPreferences: layoutService.getLayoutPreferences,
  patchLayoutPreferences: layoutService.patchLayoutPreferences,
}
