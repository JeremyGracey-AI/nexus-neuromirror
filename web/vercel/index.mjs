import { streamText } from 'ai'

const result = streamText({
  model: 'thinkingmachines/inkling',
  prompt: 'Explain quantum computing in simple terms.',
})

for await (const chunk of result.textStream) {
  process.stdout.write(chunk)
}
